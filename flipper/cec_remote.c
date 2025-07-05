#include <furi.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/scene_manager.h>
#include <gui/modules/submenu.h>
#include <gui/modules/text_input.h>
#include <gui/modules/popup.h>
#include <notification/notification_messages.h>
#include <furi_hal_gpio.h>
#include <expansion/expansion.h>
#include <string.h>
#include <stdio.h>

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
    
    char text_buffer[256];
    char custom_command[64];
    char result_buffer[1024];
    bool is_connected;
    bool uart_initialized;
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

// Simple UART Communication using GPIO bit-banging
static bool cec_remote_uart_init(CECRemoteApp* app) {
    // Initialize GPIO pins for UART
    furi_hal_gpio_init(&gpio_usart_tx, GpioModeOutputPushPull, GpioPullUp, GpioSpeedVeryHigh);
    furi_hal_gpio_init(&gpio_usart_rx, GpioModeInput, GpioPullUp, GpioSpeedVeryHigh);
    
    // Set TX line high (idle state)
    furi_hal_gpio_write(&gpio_usart_tx, true);
    
    app->uart_initialized = true;
    return true;
}

static void cec_remote_uart_deinit(CECRemoteApp* app) {
    if(app->uart_initialized) {
        furi_hal_gpio_init(&gpio_usart_tx, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
        furi_hal_gpio_init(&gpio_usart_rx, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
        app->uart_initialized = false;
    }
}

static void uart_send_byte(uint8_t byte) {
    uint32_t bit_time = 1000000 / 115200; // microseconds per bit
    
    // Start bit
    furi_hal_gpio_write(&gpio_usart_tx, false);
    furi_delay_us(bit_time);
    
    // Data bits (LSB first)
    for(int i = 0; i < 8; i++) {
        furi_hal_gpio_write(&gpio_usart_tx, (byte >> i) & 1);
        furi_delay_us(bit_time);
    }
    
    // Stop bit
    furi_hal_gpio_write(&gpio_usart_tx, true);
    furi_delay_us(bit_time);
}

static bool cec_remote_uart_send(CECRemoteApp* app, const char* data) {
    if(!app->uart_initialized) {
        return false;
    }
    
    FURI_LOG_I(TAG, "Sending UART: %s", data);
    
    // Send each character
    for(size_t i = 0; i < strlen(data); i++) {
        uart_send_byte(data[i]);
    }
    
    // Send newline
    uart_send_byte('\n');
    
    return true;
}

// Communication function - sends commands over UART
static bool cec_remote_send_command(CECRemoteApp* app, const char* command) {
    FURI_LOG_I(TAG, "Sending command: %s", command);
    
    if(!cec_remote_uart_send(app, command)) {
        strcpy(app->result_buffer, "ERROR: UART send failed");
        return false;
    }
    
    // For now, just show success message
    strcpy(app->result_buffer, "Command sent to Pi");
    return true;
}

// Menu callback
static void cec_remote_menu_callback(void* context, uint32_t index) {
    CECRemoteApp* app = context;
    
    switch(index) {
        case CECRemoteMenuPowerOn:
            strncpy(app->text_buffer, "{\"command\":\"POWER_ON\"}", sizeof(app->text_buffer) - 1);
            app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuPowerOff:
            strncpy(app->text_buffer, "{\"command\":\"POWER_OFF\"}", sizeof(app->text_buffer) - 1);
            app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuScan:
            strncpy(app->text_buffer, "{\"command\":\"SCAN\"}", sizeof(app->text_buffer) - 1);
            app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
            break;
        case CECRemoteMenuStatus:
            strncpy(app->text_buffer, "{\"command\":\"STATUS\"}", sizeof(app->text_buffer) - 1);
            app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
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
    
    const size_t max_custom_cmd_len = 50;
    
    size_t cmd_len = strlen(app->custom_command);
    if(cmd_len > max_custom_cmd_len) {
        app->custom_command[max_custom_cmd_len] = '\0';
    }
    
    snprintf(app->text_buffer, sizeof(app->text_buffer),
             "{\"command\":\"CUSTOM\",\"cec_command\":\"%.50s\"}", 
             app->custom_command);
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
}

// Scene implementations
void cec_remote_scene_start_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    popup_set_header(app->popup, "CEC Remote", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Connecting to Pi...", 64, 32, AlignCenter, AlignCenter);
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewPopup);
    
    // Initialize UART
    if(cec_remote_uart_init(app)) {
        furi_delay_ms(500);
        
        // Send PING command to test connection
        if(cec_remote_uart_send(app, "{\"command\":\"PING\"}")) {
            furi_delay_ms(1000);
            
            app->is_connected = true;
            notification_message(app->notifications, &sequence_success);
            scene_manager_next_scene(app->scene_manager, CECRemoteSceneMenu);
            return;
        }
    }
    
    // Connection failed
    app->is_connected = false;
    popup_set_header(app->popup, "Connection Failed", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Check Pi connection\nPress Back to exit", 64, 32, AlignCenter, AlignCenter);
    notification_message(app->notifications, &sequence_error);
}

bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeBack) {
        // Exit the app completely
        view_dispatcher_stop(app->view_dispatcher);
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
        app->custom_command,
        sizeof(app->custom_command),
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
    
    popup_set_header(app->popup, "Sending...", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Please wait...", 64, 32, AlignCenter, AlignCenter);
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewPopup);
    
    if(cec_remote_send_command(app, app->text_buffer)) {
        popup_set_header(app->popup, "Success", 64, 10, AlignCenter, AlignTop);
        popup_set_text(app->popup, app->result_buffer, 64, 32, AlignCenter, AlignCenter);
        notification_message(app->notifications, &sequence_success);
    } else {
        popup_set_header(app->popup, "Failed", 64, 10, AlignCenter, AlignTop);
        popup_set_text(app->popup, app->result_buffer, 64, 32, AlignCenter, AlignCenter);
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
    
    memset(app->text_buffer, 0, sizeof(app->text_buffer));
    memset(app->custom_command, 0, sizeof(app->custom_command));
    memset(app->result_buffer, 0, sizeof(app->result_buffer));
    
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
    
    app->is_connected = false;
    app->uart_initialized = false;
    
    return app;
}

static void cec_remote_app_free(CECRemoteApp* app) {
    furi_assert(app);
    
    if(app->uart_initialized) {
        cec_remote_uart_deinit(app);
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
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneStart);
    
    view_dispatcher_run(app->view_dispatcher);
    
    cec_remote_app_free(app);
    
    return 0;
}
