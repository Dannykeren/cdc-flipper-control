#include <stdint.h>
#include <stddef.h>
#include <furi.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/scene_manager.h>
#include <gui/modules/submenu.h>
#include <gui/modules/text_input.h>
#include <gui/modules/popup.h>
#include <gui/modules/text_box.h>
#include <notification/notification_messages.h>
#include <furi_hal.h>
#include <string.h>
#include <stdio.h>

#define TAG "CECRemote"

typedef enum {
    CECRemoteViewSubmenu,
    CECRemoteViewTextInput,
    CECRemoteViewPopup,
    CECRemoteViewTextBox,
} CECRemoteView;

typedef enum {
    CECRemoteSceneStart,
    CECRemoteSceneVendorSelect,
    CECRemoteSceneCommandMenu,
    CECRemoteSceneCustomCommand,
    CECRemoteSceneResult,
    CECRemoteSceneLogs,
    CECRemoteSceneNum,
} CECRemoteScene;

typedef enum {
    // Vendor selection
    CECVendorGeneric,
    CECVendorOptoma,
    CECVendorNEC,
    CECVendorEpson,
    CECVendorSamsung,
    CECVendorLG,
    CECVendorViewLogs,
    CECVendorClearLogs,
} CECVendorMenuItem;

typedef enum {
    // Command menu items
    CECCommandPowerOn,
    CECCommandPowerOff,
    CECCommandHDMI1,
    CECCommandHDMI2,
    CECCommandHDMI3,
    CECCommandHDMI4,
    CECCommandVolumeUp,
    CECCommandVolumeDown,
    CECCommandMute,
    CECCommandScan,
    CECCommandStatus,
    CECCommandCustom,
    CECCommandBack,
} CECCommandMenuItem;

typedef struct {
    Gui* gui;
    ViewDispatcher* view_dispatcher;
    SceneManager* scene_manager;
    Submenu* submenu;
    TextInput* text_input;
    Popup* popup;
    TextBox* text_box;
    NotificationApp* notifications;
    
    char text_buffer[256];
    char custom_command[64];
    char result_buffer[1024];
    char log_buffer[2048];
    bool is_connected;
    bool uart_initialized;
    
    // Current vendor selection
    uint8_t selected_vendor;
    
    FuriHalSerialHandle* serial_handle;
    FuriStreamBuffer* rx_stream;
    FuriTimer* cleanup_timer;
} CECRemoteApp;

// Command definitions by vendor
typedef struct {
    const char* name;
    const char* command;
} CECCommand;

// Generic commands
static const CECCommand generic_commands[] = {
    {"POWER_ON", "{\"command\":\"POWER_ON\"}"},
    {"POWER_OFF", "{\"command\":\"POWER_OFF\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:10:00\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:20:00\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:30:00\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:40:00\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"volup\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"voldown\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"mute\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// Samsung-specific commands
static const CECCommand samsung_commands[] = {
    {"POWER_ON", "{\"command\":\"CUSTOM\",\"cec_command\":\"on 0\"}"},
    {"POWER_OFF", "{\"command\":\"CUSTOM\",\"cec_command\":\"standby 0\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:10:00\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:20:00\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:30:00\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:82:40:00\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:44:41\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:44:42\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 4F:44:43\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// Optoma-specific commands
static const CECCommand optoma_commands[] = {
    {"POWER_ON", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:04\"}"},
    {"POWER_OFF", "{\"command\":\"CUSTOM\",\"cec_command\":\"standby 0\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:10:00\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:20:00\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:30:00\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:40:00\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:41\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:42\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:43\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// NEC-specific commands
static const CECCommand nec_commands[] = {
    {"POWER_ON", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:04\"}"},
    {"POWER_OFF", "{\"command\":\"CUSTOM\",\"cec_command\":\"standby 0\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:10:00\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:20:00\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:30:00\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:40:00\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:41\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:42\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:43\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// Epson-specific commands
static const CECCommand epson_commands[] = {
    {"POWER_ON", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:04\"}"},
    {"POWER_OFF", "{\"command\":\"CUSTOM\",\"cec_command\":\"standby 0\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:10:00\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:20:00\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:30:00\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:82:40:00\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:41\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:42\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:43\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// LG-specific commands
static const CECCommand lg_commands[] = {
    {"POWER_ON", "{\"command\":\"CUSTOM\",\"cec_command\":\"on 0\"}"},
    {"POWER_OFF", "{\"command\":\"CUSTOM\",\"cec_command\":\"standby 0\"}"},
    {"HDMI_1", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:F1\"}"},
    {"HDMI_2", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:F2\"}"},
    {"HDMI_3", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:F3\"}"},
    {"HDMI_4", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:F4\"}"},
    {"VOLUME_UP", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:41\"}"},
    {"VOLUME_DOWN", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:42\"}"},
    {"MUTE", "{\"command\":\"CUSTOM\",\"cec_command\":\"tx 10:44:43\"}"},
    {"SCAN", "{\"command\":\"SCAN\"}"},
    {"STATUS", "{\"command\":\"STATUS\"}"},
};

// Get commands for selected vendor
static const CECCommand* get_vendor_commands(uint8_t vendor) {
    switch(vendor) {
        case CECVendorSamsung: return samsung_commands;
        case CECVendorOptoma: return optoma_commands;
        case CECVendorNEC: return nec_commands;
        case CECVendorEpson: return epson_commands;
        case CECVendorLG: return lg_commands;
        default: return generic_commands;
    }
}

static const char* get_vendor_name(uint8_t vendor) {
    switch(vendor) {
        case CECVendorSamsung: return "Samsung";
        case CECVendorOptoma: return "Optoma";
        case CECVendorNEC: return "NEC";
        case CECVendorEpson: return "Epson";
        case CECVendorLG: return "LG";
        default: return "Generic";
    }
}

// Forward declarations
void cec_remote_scene_start_on_enter(void* context);
bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_start_on_exit(void* context);
void cec_remote_scene_vendor_select_on_enter(void* context);
bool cec_remote_scene_vendor_select_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_vendor_select_on_exit(void* context);
void cec_remote_scene_command_menu_on_enter(void* context);
bool cec_remote_scene_command_menu_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_command_menu_on_exit(void* context);
void cec_remote_scene_custom_on_enter(void* context);
bool cec_remote_scene_custom_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_custom_on_exit(void* context);
void cec_remote_scene_result_on_enter(void* context);
bool cec_remote_scene_result_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_result_on_exit(void* context);
void cec_remote_scene_logs_on_enter(void* context);
bool cec_remote_scene_logs_on_event(void* context, SceneManagerEvent event);
void cec_remote_scene_logs_on_exit(void* context);

// Timer callback for safe cleanup
static void cec_remote_cleanup_timer_callback(void* context) {
    CECRemoteApp* app = (CECRemoteApp*)context;
    view_dispatcher_stop(app->view_dispatcher);
}

// RX callback for receiving data
static void cec_remote_uart_rx_callback(FuriHalSerialHandle* handle, FuriHalSerialRxEvent event, void* context) {
    CECRemoteApp* app = (CECRemoteApp*)context;
    
    if(event == FuriHalSerialRxEventData) {
        uint8_t byte = furi_hal_serial_async_rx(handle);
        furi_stream_buffer_send(app->rx_stream, &byte, 1, 0);
    }
}

// UART initialization
static bool cec_remote_uart_init(CECRemoteApp* app) {
    app->serial_handle = furi_hal_serial_control_acquire(FuriHalSerialIdUsart);
    if(!app->serial_handle) {
        FURI_LOG_E(TAG, "Failed to acquire USART");
        return false;
    }
    
    furi_hal_serial_init(app->serial_handle, 115200);
    app->rx_stream = furi_stream_buffer_alloc(1024, 1);
    furi_hal_serial_async_rx_start(app->serial_handle, cec_remote_uart_rx_callback, app, false);
    
    app->uart_initialized = true;
    FURI_LOG_I(TAG, "UART initialized successfully");
    return true;
}

static void cec_remote_uart_deinit(CECRemoteApp* app) {
    if(app->uart_initialized) {
        furi_hal_serial_async_rx_stop(app->serial_handle);
        
        if(app->rx_stream) {
            furi_stream_buffer_free(app->rx_stream);
            app->rx_stream = NULL;
        }
        
        furi_hal_serial_deinit(app->serial_handle);
        furi_hal_serial_control_release(app->serial_handle);
        app->serial_handle = NULL;
        
        app->uart_initialized = false;
        FURI_LOG_I(TAG, "UART deinitialized safely");
    }
}

static bool cec_remote_uart_send(CECRemoteApp* app, const char* data) {
    if(!app->uart_initialized || !app->serial_handle) {
        return false;
    }
    
    FURI_LOG_I(TAG, "Sending: %s", data);
    
    furi_hal_serial_tx(app->serial_handle, (uint8_t*)data, strlen(data));
    furi_hal_serial_tx(app->serial_handle, (uint8_t*)"\n", 1);
    furi_hal_serial_tx_wait_complete(app->serial_handle);
    
    return true;
}

static bool cec_remote_uart_receive(CECRemoteApp* app, char* buffer, size_t buffer_size, uint32_t timeout_ms) {
    if(!app->uart_initialized || !app->serial_handle || !app->rx_stream) {
        return false;
    }
    
    uint32_t start_time = furi_get_tick();
    size_t total_received = 0;
    
    while(furi_get_tick() - start_time < timeout_ms && total_received < buffer_size - 1) {
        uint8_t byte;
        if(furi_stream_buffer_receive(app->rx_stream, &byte, 1, 50) > 0) {
            if(byte == '\n' || byte == '\r') {
                buffer[total_received] = '\0';
                if(total_received > 0) {
                    FURI_LOG_I(TAG, "Received: %s", buffer);
                    return true;
                }
            } else if(byte >= 32 && byte <= 126) {
                buffer[total_received++] = byte;
            }
        }
    }
    
    buffer[total_received] = '\0';
    return total_received > 0;
}

// Extract result from JSON response
static void extract_result_from_json(const char* json_response, char* result_buffer, size_t buffer_size) {
    // Simple JSON parsing to extract the "result" field
    const char* result_start = strstr(json_response, "\"result\":\"");
    if(result_start) {
        result_start += 10; // Skip "result":"
        const char* result_end = strstr(result_start, "\",");
        if(!result_end) {
            result_end = strstr(result_start, "\"}");
        }
        if(result_end) {
            size_t result_len = result_end - result_start;
            if(result_len < buffer_size - 1) {
                strncpy(result_buffer, result_start, result_len);
                result_buffer[result_len] = '\0';
                return;
            }
        }
    }
    
    // Fallback: check for simple success/error
    if(strstr(json_response, "\"status\":\"success\"")) {
        strncpy(result_buffer, "✅ Command sent successfully", buffer_size - 1);
    } else if(strstr(json_response, "\"status\":\"error\"")) {
        strncpy(result_buffer, "❌ Command failed", buffer_size - 1);
    } else {
        strncpy(result_buffer, "Unknown response", buffer_size - 1);
    }
    result_buffer[buffer_size - 1] = '\0';
}

// Send command and get clean response
static bool cec_remote_send_command(CECRemoteApp* app, const char* command) {
    FURI_LOG_I(TAG, "Sending command: %s", command);
    
    if(!cec_remote_uart_send(app, command)) {
        strcpy(app->result_buffer, "❌ UART send failed");
        return false;
    }
    
    char raw_response[1024];
    if(!cec_remote_uart_receive(app, raw_response, sizeof(raw_response), 5000)) {
        strcpy(app->result_buffer, "❌ No response from Pi");
        return false;
    }
    
    // Extract clean result from JSON
    extract_result_from_json(raw_response, app->result_buffer, sizeof(app->result_buffer));
    
    return true;
}

// Vendor selection callback
static void cec_remote_vendor_callback(void* context, uint32_t index) {
    CECRemoteApp* app = context;
    
    if(index == CECVendorViewLogs) {
        scene_manager_next_scene(app->scene_manager, CECRemoteSceneLogs);
    } else if(index == CECVendorClearLogs) {
        strncpy(app->text_buffer, "{\"command\":\"CLEAR_FLIPPER_LOG\"}", sizeof(app->text_buffer) - 1);
        app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
        scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
    } else {
        app->selected_vendor = index;
        scene_manager_next_scene(app->scene_manager, CECRemoteSceneCommandMenu);
    }
}

// Command menu callback
static void cec_remote_command_callback(void* context, uint32_t index) {
    CECRemoteApp* app = context;
    
    if(index == CECCommandBack) {
        scene_manager_previous_scene(app->scene_manager);
        return;
    }
    
    if(index == CECCommandCustom) {
        scene_manager_next_scene(app->scene_manager, CECRemoteSceneCustomCommand);
        return;
    }
    
    // Get the command for this vendor
    const CECCommand* commands = get_vendor_commands(app->selected_vendor);
    strncpy(app->text_buffer, commands[index].command, sizeof(app->text_buffer) - 1);
    app->text_buffer[sizeof(app->text_buffer) - 1] = '\0';
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
}

// Text input callback
static void cec_remote_text_input_callback(void* context) {
    CECRemoteApp* app = context;
    
    snprintf(app->text_buffer, sizeof(app->text_buffer),
             "{\"command\":\"CUSTOM\",\"cec_command\":\"%.50s\"}", 
             app->custom_command);
    
    scene_manager_next_scene(app->scene_manager, CECRemoteSceneResult);
}

// Scene implementations
void cec_remote_scene_start_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    popup_set_header(app->popup, "CEC Remote v2.0", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Connecting to Pi...", 64, 32, AlignCenter, AlignCenter);
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewPopup);
    
    if(cec_remote_uart_init(app)) {
        furi_delay_ms(500);
        
        if(cec_remote_uart_send(app, "{\"command\":\"PING\"}")) {
            char response[256];
            if(cec_remote_uart_receive(app, response, sizeof(response), 3000)) {
                if(strstr(response, "success") || strstr(response, "pong")) {
                    app->is_connected = true;
                    notification_message(app->notifications, &sequence_success);
                    popup_set_header(app->popup, "Connected!", 64, 10, AlignCenter, AlignTop);
                    popup_set_text(app->popup, "Ready to control CEC devices", 64, 32, AlignCenter, AlignCenter);
                    furi_delay_ms(1000);
                    scene_manager_next_scene(app->scene_manager, CECRemoteSceneVendorSelect);
                    return;
                }
            }
        }
    }
    
    app->is_connected = false;
    popup_set_header(app->popup, "Connection Failed", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Check Pi connection\nPress Back to exit", 64, 32, AlignCenter, AlignCenter);
    notification_message(app->notifications, &sequence_error);
}

bool cec_remote_scene_start_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeBack) {
        // Start timer for safe cleanup
        furi_timer_start(app->cleanup_timer, 100);
        consumed = true;
    }
    
    return consumed;
}

void cec_remote_scene_start_on_exit(void* context) {
    CECRemoteApp* app = context;
    popup_reset(app->popup);
}

void cec_remote_scene_vendor_select_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    submenu_reset(app->submenu);
    submenu_set_header(app->submenu, "Select Device Brand");
    
    submenu_add_item(app->submenu, "Generic/Unknown", CECVendorGeneric, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "Samsung TV", CECVendorSamsung, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "Optoma Projector", CECVendorOptoma, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "NEC Projector", CECVendorNEC, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "Epson Projector", CECVendorEpson, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "LG TV", CECVendorLG, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "--- Logs ---", CECVendorViewLogs, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "View Logs", CECVendorViewLogs, cec_remote_vendor_callback, app);
    submenu_add_item(app->submenu, "Clear Logs", CECVendorClearLogs, cec_remote_vendor_callback, app);
    
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewSubmenu);
}

bool cec_remote_scene_vendor_select_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeBack) {
        // Start timer for safe cleanup
        furi_timer_start(app->cleanup_timer, 100);
        consumed = true;
    }
    
    return consumed;
}

void cec_remote_scene_vendor_select_on_exit(void* context) {
    CECRemoteApp* app = context;
    submenu_reset(app->submenu);
}

void cec_remote_scene_command_menu_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    submenu_reset(app->submenu);
    
    char header[64];
    snprintf(header, sizeof(header), "%s Commands", get_vendor_name(app->selected_vendor));
    submenu_set_header(app->submenu, header);
    
    submenu_add_item(app->submenu, "🔌 Power ON", CECCommandPowerOn, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "⏸️ Power OFF", CECCommandPowerOff, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "📺 HDMI 1", CECCommandHDMI1, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "📺 HDMI 2", CECCommandHDMI2, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "📺 HDMI 3", CECCommandHDMI3, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "📺 HDMI 4", CECCommandHDMI4, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "🔊 Volume UP", CECCommandVolumeUp, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "🔉 Volume DOWN", CECCommandVolumeDown, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "🔇 Mute", CECCommandMute, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "🔍 Scan Devices", CECCommandScan, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "ℹ️ Status", CECCommandStatus, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "⚙️ Custom Command", CECCommandCustom, cec_remote_command_callback, app);
    submenu_add_item(app->submenu, "⬅️ Back", CECCommandBack, cec_remote_command_callback, app);
    
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewSubmenu);
}

bool cec_remote_scene_command_menu_on_event(void* context, SceneManagerEvent event) {
    UNUSED(context);
    UNUSED(event);
    return false;
}

void cec_remote_scene_command_menu_on_exit(void* context) {
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
    
    // Send command and get clean response
    if(cec_remote_send_command(app, app->text_buffer)) {
        popup_set_header(app->popup, "Result", 64, 10, AlignCenter, AlignTop);
        popup_set_text(app->popup, app->result_buffer, 64, 32, AlignCenter, AlignCenter);
        
        if(strstr(app->result_buffer, "✅")) {
            notification_message(app->notifications, &sequence_success);
        } else {
            notification_message(app->notifications, &sequence_error);
        }
    } else {
        popup_set_header(app->popup, "Error", 64, 10, AlignCenter, AlignTop);
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

void cec_remote_scene_logs_on_enter(void* context) {
    CECRemoteApp* app = context;
    
    // Request logs from Pi
    memset(app->log_buffer, 0, sizeof(app->log_buffer));
    
    text_box_reset(app->text_box);
    text_box_set_text(app->text_box, "Loading logs...");
    view_dispatcher_switch_to_view(app->view_dispatcher, CECRemoteViewTextBox);
    
    // Send log request
    if(cec_remote_uart_send(app, "{\"command\":\"GET_FLIPPER_LOG\"}")) {
        char response[2048];
        if(cec_remote_uart_receive(app, response, sizeof(response), 5000)) {
            // Extract log content from JSON response
            const char* result_start = strstr(response, "\"result\":\"");
            if(result_start) {
                result_start += 10; // Skip "result":"
                const char* result_end = strstr(result_start, "\"}");
                if(result_end) {
                    size_t result_len = result_end - result_start;
                    if(result_len < sizeof(app->log_buffer) - 1) {
                        strncpy(app->log_buffer, result_start, result_len);
                        app->log_buffer[result_len] = '\0';
                        
                        // Replace \n with actual newlines
                        char* pos = app->log_buffer;
                        while((pos = strstr(pos, "\\n")) != NULL) {
                            *pos = '\n';
                            memmove(pos + 1, pos + 2, strlen(pos + 2) + 1);
                        }
                        
                        text_box_set_text(app->text_box, app->log_buffer);
                        return;
                    }
                }
            }
        }
    }
    
    text_box_set_text(app->text_box, "❌ Failed to load logs\nPress Back to return");
}

bool cec_remote_scene_logs_on_event(void* context, SceneManagerEvent event) {
    CECRemoteApp* app = context;
    bool consumed = false;
    
    if(event.type == SceneManagerEventTypeBack) {
        scene_manager_previous_scene(app->scene_manager);
        consumed = true;
    }
    
    return consumed;
}

void cec_remote_scene_logs_on_exit(void* context) {
    CECRemoteApp* app = context;
    text_box_reset(app->text_box);
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
    cec_remote_scene_vendor_select_on_enter,
    cec_remote_scene_command_menu_on_enter,
    cec_remote_scene_custom_on_enter,
    cec_remote_scene_result_on_enter,
    cec_remote_scene_logs_on_enter,
};

bool (*const cec_remote_scene_on_event_handlers[])(void*, SceneManagerEvent) = {
    cec_remote_scene_start_on_event,
    cec_remote_scene_vendor_select_on_event,
    cec_remote_scene_command_menu_on_event,
    cec_remote_scene_custom_on_event,
    cec_remote_scene_result_on_event,
    cec_remote_scene_logs_on_event,
};

void (*const cec_remote_scene_on_exit_handlers[])(void*) = {
    cec_remote_scene_start_on_exit,
    cec_remote_scene_vendor_select_on_exit,
    cec_remote_scene_command_menu_on_exit,
    cec_remote_scene_custom_on_exit,
    cec_remote_scene_result_on_exit,
    cec_remote_scene_logs_on_exit,
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
    memset(app->log_buffer, 0, sizeof(app->log_buffer));
    
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
    
    app->text_box = text_box_alloc();
    view_dispatcher_add_view(app->view_dispatcher, CECRemoteViewTextBox, text_box_get_view(app->text_box));
    
    app->is_connected = false;
    app->uart_initialized = false;
    app->serial_handle = NULL;
    app->rx_stream = NULL;
    app->selected_vendor = CECVendorGeneric;
    
    // Create cleanup timer
    app->cleanup_timer = furi_timer_alloc(cec_remote_cleanup_timer_callback, FuriTimerTypeOnce, app);
    
    return app;
}

static void cec_remote_app_free(CECRemoteApp* app) {
    furi_assert(app);
    
    // Stop and free timer
    if(app->cleanup_timer) {
        furi_timer_stop(app->cleanup_timer);
        furi_timer_free(app->cleanup_timer);
    }
    
    // Safely cleanup UART
    if(app->uart_initialized) {
        cec_remote_uart_deinit(app);
    }
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewSubmenu);
    submenu_free(app->submenu);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewTextInput);
    text_input_free(app->text_input);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewPopup);
    popup_free(app->popup);
    
    view_dispatcher_remove_view(app->view_dispatcher, CECRemoteViewTextBox);
    text_box_free(app->text_box);
    
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
