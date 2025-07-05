#include <furi.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/scene_manager.h>
#include <gui/modules/submenu.h>
#include <gui/modules/text_input.h>
#include <gui/modules/popup.h>
#include <notification/notification_messages.h>
#include <expansion/expansion.h>

#define TAG "CECRemote"

typedef enum {
    CECRemoteViewSubmenu,
    CECRemoteViewTextInput,
    CECRemoteViewPopup,
} CECRemoteView;

typedef enum {
    CECRemoteSceneStart,
    CECRemoteSceneMenu,
    CECRemoteSceneCustomCommand,
    CECRemoteSceneResult,
} CECRemoteScene;

typedef enum {
    CECRemoteMenuPowerOn,
    CECRemoteMenuPowerOff,
    CECRemoteMenuScan,
    CECRemoteMenuStatus,
    CECRemoteMenuCustom,
} CECRemoteMenuItem;

typedef struct {
    Gui* gui;
    ViewDispatcher* view_dispatcher;
    SceneManager* scene_manager;
    Submenu* submenu;
    TextInput* text_input;
    Popup* popup;
    NotificationApp* notifications;
    
    Expansion* expansion;
    FuriStreamBuffer* uart_stream;
    FuriThread* worker_thread;
    
    char text_buffer[256];
    char result_buffer[1024];
    bool is_connected;
} CECRemoteApp;

// Forward declarations
void cec_remote_scene_start_on_enter(void* context);
bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_start_on_exit(void* context);
void cec_remote_scene_menu_on_enter(void* context);
bool cec_remote_scene_menu_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_menu_on_exit(void* context);
void cec_remote_scene_custom_on_enter(void* context);
bool cec_remote_scene_custom_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_custom_on_exit(void* context);
void cec_remote_scene_result_on_enter(void* context);
bool cec_remote_scene_result_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_result_on_exit(void* context);

// Scene handlers table
void (*const cec_remote_scene_on_enter_handlers[])(void*) = {
    cec_remote_scene_start_on_enter,
    cec_remote_scene_menu_on_enter,
    cec_remote_scene_custom_on_enter,
    cec_remote_scene_result_on_enter,
};

bool (*const cec_remote_scene_on_event_handlers[])(void*, SceneManagerEvent) = {
    cec_remote_scene_start_on_event,
    cec_remote_scene_menu_on_event,
    cec_remote_scene_custom_on_event,
    cec_remote_scene_result_on_event,
};

void (*const cec_remote_scene_on_exit_handlers[])(void*) = {
    cec_remote_scene_start_on_exit,
    cec_remote_scene_menu_on_exit,
    cec_remote_scene_custom_on_exit,
    cec_remote_scene_result_on_exit,
};

// Worker thread for UART communication
static int32_t cec_remote_worker(void* context) {
    CECRemoteApp* app = context;
    
    while(true) {
        if(app->expansion) {
            uint8_t buffer[64];
            size_t received = expansion_rx(app->expansion, buffer, sizeof(buffer) - 1, 100);
            if(received > 0) {
                buffer[received] = '\0';
                furi_stream_buffer_send(app->uart_stream, buffer, received, 0);
            }
        } else {
            furi_delay_ms(100);
        }
        
        if(furi_thread_flags_get() & FuriThreadFlagExitRequest) {
            break;
        }
    }
    
    return 0;
}

// Communication functions
static bool cec_remote_send_command(CECRemoteApp* app, const char* command) {
    if(!app->expansion || !app->is_connected) {
        return false;
    }
    
    size_t command_len = strlen(command);
    size_t sent = expansion_tx(app->expansion, (uint8_t*)command, command_len);
    expansion_tx(app->expansion, (uint8_t*)"\n", 1);
    
    return sent == command_len;
}

static bool cec_remote_wait_response(CECRemoteApp* app, uint32_t timeout_ms) {
    uint32_t start_time = furi_get_tick();
    size_t received = 0;
    
    while((furi_get_tick() - start_time) < timeout_ms) {
        size_t available = furi_stream_buffer_bytes_available(app->uart_stream);
        if(available > 0) {
            uint8_t buffer[64];
            size_t read = furi_stream_buffer_receive(app->uart_stream, buffer, sizeof(buffer) - 1, 10);
            if(read > 0) {
                buffer[read] = '\0';
                
                if(received + read < sizeof(app->result_buffer) - 1) {
                    strcat(app->result_buffer + received, (char*)buffer);
                    received += read;
                }
                
                if(strchr((char*)buffer, '}')) {
                    return true;
                }
            }
        }
        furi_delay_ms(10);
    }
    
    return received > 0;
}

// Menu callback
static void cec_remote_menu_callback(void* context, uint32_t index) {
    CECRemoteApp* app = context;
    
    switch(index) {
        case CECRemoteMenuPowerOn:
            strcpy(app->text_buffer, "{\"command\":\"POWER_ON\"}");
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuPowerOff:
            strcpy(app->text_buffer, "{\"command\":\"POWER_OFF\"}");
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuScan:
            strcpy(app->text_buffer, "{\"command\":\"SCAN\"}");
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuStatus:
            strcpy(app->text_buffer, "{\"command\":\"STATUS\"}");
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuCustom:
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneCustomCommand);
            break;
    }
}

// Text input callback
static void cec_remote_text_input_callback(void* context) {
    CECRemoteApp* app = context;
    
    snprintf(app->text_buffer, sizeof(app->text_buffer), 
             "{\"command\":\"CUSTOM\",\"cec_command\":\"%s\"}", 
             app->text_buffer);
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
}

// Scene implementations
void cec_remote_scene_start_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    app->expansion = expansion_alloc();
    if(app->expansion) {
        if(expansion_open(app->expansion)) {
            app->is_connected = true;
            notification_message(app->notifications, &sequence_success);
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneMenu);
        } else {
            app->is_connected = false;
            popup_set_header(app->popup, "Connection Failed", 64, 10, AlignCenter, AlignTop);
            popup_set_text(app->popup, "Connect RPi via USB\nand try again", 64, 32, AlignCenter, AlignCenter);
            view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewPopup);
        }
    }
}

bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeCustom) {
        scene_manager_next_scene(app->scene_manager, CECRemoteSceneMenu);
        consumed = true;
    }
    
    return consumed;
}

void cec_remote_scene_start_on_exit(void* context) {
    CECRemoteApp* app = context;
    popup_reset(app->popup);
}

void cec_remote_scene_menu_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    submenu_reset(app->submenu);
    submenu_set_header(app->submenu, "CEC Remote Control");
    
    submenu_add_item(app->submenu, "Power ON", CECRemoteMenuPowerOn, cec_remote_menu_callback, app);
    submenu_add_item(app->submenu, "Power OFF", CECRemoteMenuPowerOff, cec_remote_menu_callback, app);
    submenu_add_item(app->submenu, "Scan Devices", CECRemoteMenuScan, cec_remote_menu_callback, app);
    submenu_add_item(app->submenu, "Check Status", CECRemoteMenuStatus, cec_remote_menu_callback, app);
    submenu_add_item(app->submenu, "Custom Command", CECRemoteMenuCustom, cec_remote_menu_callback, app);
    
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewSubmenu);
}

bool cec_remote_scene_menu_on_event(void* context, SceneManagerEvent event) {
    UNUSED(context);
    UNUSED(event);
    return false;
}

void cec_remote_scene_menu_on_exit(void* context) {
    CECRemoteApp* app = context;
    submenu_reset(app->submenu);
}

void cec_remote_scene_custom_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    text_input_reset(app->text_input);
    text_input_set_header_text(app->text_input, "Enter CEC Command:");
    text_input_set_result_callback(
        app->text_input,
        cec_remote_text_input_callback,
        app,
        app->text_buffer,
        sizeof(app->text_buffer),
        true);
    
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewTextInput);
}

bool cec_remote_scene_custom_on_event(void* context, SceneManagerEvent event) {
    UNUSED(context);
    UNUSED(event);
    return false;
}

void cec_remote_scene_custom_on_exit(void* context) {
    CECRemoteApp* app = context;
    text_input_reset(app->text_input);
}

void cec_remote_scene_result_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    memset(app->result_buffer, 0, sizeof(app->result_buffer));
    
    popup_set_header(app->popup, "Sending Command...", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Please wait...", 64, 32, AlignCenter, AlignCenter);
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewPopup);
    
    if(cec_remote_send_command(app, app->text_buffer)) {
        if(cec_remote_wait_response(app, 5000)) {
            popup_set_header(app->popup, "Command Sent", 64, 10, AlignCenter, AlignTop);
            popup_set_text(app->popup, "Press Back to continue", 64, 50, AlignCenter, AlignCenter);
            notification_message(app->notifications, &sequence_success);
        } else {
            popup_set_header(app->popup, "Timeout", 64, 10, AlignCenter, AlignTop);
            popup_set_text(app->popup, "No response from RPi\nPress Back to continue", 64, 32, AlignCenter, AlignCenter);
            notification_message(app->notifications, &sequence_error);
        }
    } else {
        popup_set_header(app->popup, "Send Failed", 64, 10, AlignCenter, AlignTop);
        popup_set_text(app->popup, "Check USB connection\nPress Back to continue", 64, 32, AlignCenter, AlignCenter);
        notification_message(app->notifications, &sequence_error);
    }
}

bool cec_remote_scene_result_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeBack) {
        scene_manager_previous_scene(app->scene_manager);
        consumed = true;
    }
    
    return consumed;
}

void cec_remote_scene_result_on_exit(void* context) {
    CECRemoteApp* app = context;
    popup_reset(app->popup);
}

// View dispatcher callbacks
static bool cec_remote_view_dispatcher_navigation_event_callback(void* context) {
    CECRemoteApp* app = context;
    return scene_manager_handle_back_event(app->scene_manager);
}

static bool cec_remote_view_dispatcher_custom_event_callback(void* context, uint32_t event) {
    CECRemoteApp* app = context;
    return scene_manager_handle_custom_event(app->scene_manager, event);
}

// App allocation and deallocation
static CECRemoteApp* cec_remote_app_alloc(void) {
    CECRemoteApp* app = malloc(sizeof(CECRemoteApp));
    
    app->gui = furi_record_open(RECORD_GUI);
    app->notifications = furi_record_open(RECORD_NOTIFICATION);
    
    app->view_dispatcher = view_dispatcher_alloc();
    view_dispatcher_enable_queue(app->view_dispatcher);
    view_dispatcher_set_event_callback_context(app->view_dispatcher, app);
    view_dispatcher_set_navigation_event_callback(
        app->view_dispatcher, cec_remote_view_dispatcher_navigation_event_callback);
    view_dispatcher_set_custom_event_callback(
        app->view_dispatcher, cec_remote_view_dispatcher_custom_event_callback);
    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);
    
    app->scene_manager = scene_manager_alloc(
        &cec_remote_scene_on_enter_handlers,
        &cec_remote_scene_on_event_handlers,
        &cec_remote_scene_on_exit_handlers);
    scene_manager_set_context(app->scene_manager, app);
    
    app->submenu = submenu_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewSubmenu, submenu_get_view(app->submenu));
    
    app->text_input = text_input_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewTextInput, text_input_get_view(app->text_input));
    
    app->popup = popup_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewPopup, popup_get_view(app->popup));
    
    app->uart_stream = furi_stream_buffer_alloc(1024, 1);
    app->worker_thread = furi_thread_alloc_ex("CECRemoteWorker", 1024, cec_remote_worker, app);
    
    app->expansion = NULL;
    app->is_connected = false;
    
    return app;
}

static void cec_remote_app_free(CECRemoteApp* app) {
    furi_assert(app);
    
    furi_thread_flags_set(furi_thread_get_id(app->worker_thread), FuriThreadFlagExitRequest);
    furi_thread_join(app->worker_thread);
    furi_thread_free(app->worker_thread);
    
    furi_stream_buffer_free(app->uart_stream);
    
    if(app->expansion) {
        expansion_close(app->expansion);
        expansion_free(app->expansion);
    }
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewSubmenu);
    submenu_free(app->submenu);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewTextInput);
    text_input_free(app->text_input);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewPopup);
    popup_free(app->popup);
    
    scene_manager_free(app->scene_manager);
    view_dispatcher_free(app->view_dispatcher);
    
    furi_record_close(RECORD_NOTIFICATION);
    furi_record_close(RECORD_GUI);
    
    free(app);
}

// Main application entry point
int32_t cec_remote_app(void* p) {
    UNUSED(p);
    
    CECRemoteApp* app = cec_remote_app_alloc();
    
    furi_thread_start(app->worker_thread);
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneStart);
    
    view_dispatcher_run(app->view_dispatcher);
    
    cec_remote_app_free(app);
    
    return 0;
}
