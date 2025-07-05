#include <furi.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/scene_manager.h>
#include <gui/modules/submenu.h>
#include <gui/modules/text_input.h>
#include <gui/modules/popup.h>
#include <notification/notification_messages.h>
#include <furi_hal_uart.h>

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
    CECRemoteSceneNum,
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
    
    FuriStreamBuffer* uart_stream;
    FuriThread* worker_thread;
    
    char text_buffer[256];
    char result_buffer[1024];
    bool is_connected;
    bool worker_running;
} CECRemoteApp;

// Worker thread for UART communication
static int32_t cec_remote_worker(void* context) {
    CECRemoteApp* app = context;
    
    while(app->worker_running) {
        // Simulate USB serial communication
        // In a real implementation, this would read from the USB UART
        furi_delay_ms(100);
        
        if(furi_thread_flags_get() & FuriThreadFlagExitRequest) {
            break;
        }
    }
    
    return 0;
}

// Communication functions
static bool cec_remote_send_command(CECRemoteApp* app, const char* command) {
    if(!app->is_connected) {
        return false;
    }
    
    // For now, just log the command
    FURI_LOG_I(TAG, "Sending command: %s", command);
    
    // In a real implementation, this would send via USB UART
    // For testing, we'll simulate success
    return true;
}

static bool cec_remote_wait_response(CECRemoteApp* app, uint32_t timeout_ms) {
    UNUSED(app);
    UNUSED(timeout_ms);
    
    // Simulate response received
    furi_delay_ms(500);
    return true;
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
    
    // Format custom command
    char temp[256];
    snprintf(temp, sizeof(temp), "%s", app->text_buffer);
    snprintf(app->text_buffer, sizeof(app->text_buffer), 
             "{\"command\":\"CUSTOM\",\"cec_command\":\"%s\"}", temp);
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
}

// Scene implementations
void cec_remote_scene_start_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    // For now, assume connection is successful
    app->is_connected = true;
    notification_message(app->notifications, &sequence_success);
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneMenu);
}

bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event) {
    UNUSED(context);
    UNUSED(event);
    return false;
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

// Scene handlers
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

const SceneManagerHandlers cec_remote_scene_handlers = {
    .on_enter_handlers = cec_remote_scene_on_enter_handlers,
    .on_event_handlers = cec_remote_scene_on_event_handlers,
    .on_exit_handlers = cec_remote_scene_on_exit_handlers,
    .scene_num = CECRemoteSceneNum,
};

// App allocation and deallocation
static CECRemoteApp* cec_remote_app_alloc(void) {
    CECRemoteApp* app = malloc(sizeof(CECRemoteApp));
    
    app->gui = furi_record_open(RECORD_GUI);
    app->notifications = furi_record_open(RECORD_NOTIFICATION);
    
    app->view_dispatcher = view_dispatcher_alloc();
    view_dispatcher_set_event_callback_context(app->view_dispatcher, app);
    view_dispatcher_set_navigation_event_callback(
        app->view_dispatcher, cec_remote_view_dispatcher_navigation_event_callback);
    view_dispatcher_set_custom_event_callback(
        app->view_dispatcher, cec_remote_view_dispatcher_custom_event_callback);
    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);
    
    app->scene_manager = scene_manager_alloc(&cec_remote_scene_handlers, app);
    
    app->submenu = submenu_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewSubmenu, submenu_get_view(app->submenu));
    
    app->text_input = text_input_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewTextInput, text_input_get_view(app->text_input));
    
    app->popup = popup_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewPopup, popup_get_view(app->popup));
    
    app->uart_stream = furi_stream_buffer_alloc(1024, 1);
    app->worker_thread = furi_thread_alloc_ex("CECRemoteWorker", 1024, cec_remote_worker, app);
    
    app->is_connected = false;
    app->worker_running = false;
    
    return app;
}

static void cec_remote_app_free(CECRemoteApp* app) {
    furi_assert(app);
    
    // Stop worker thread
    app->worker_running = false;
    furi_thread_flags_set(furi_thread_get_id(app->worker_thread), FuriThreadFlagExitRequest);
    furi_thread_join(app->worker_thread);
    furi_thread_free(app->worker_thread);
    
    // Free UART stream
    furi_stream_buffer_free(app->uart_stream);
    
    // Free views
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewSubmenu);
    submenu_free(app->submenu);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewTextInput);
    text_input_free(app->text_input);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewPopup);
    popup_free(app->popup);
    
    // Free scene manager and view dispatcher
    scene_manager_free(app->scene_manager);
    view_dispatcher_free(app->view_dispatcher);
    
    // Close records
    furi_record_close(RECORD_NOTIFICATION);
    furi_record_close(RECORD_GUI);
    
    free(app);
}

// Main application entry point
int32_t cec_remote_app(void* p) {
    UNUSED(p);
    
    CECRemoteApp* app = cec_remote_app_alloc();
    
    // Start worker thread
    app->worker_running = true;
    furi_thread_start(app->worker_thread);
    
    // Start with the connection scene
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneStart);
    
    // Run the app
    view_dispatcher_run(app->view_dispatcher);
    
    // Cleanup
    cec_remote_app_free(app);
    
    return 0;
}
