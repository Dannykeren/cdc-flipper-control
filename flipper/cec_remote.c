#include <stdint.h>
#include <stddef.h>
#include <furi.h>
#include <furi_hal_gpio.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/modules/popup.h>

typedef struct {
    Gui* gui;
    ViewDispatcher* view_dispatcher;
    Popup* popup;
} SimpleGPIOApp;

// Simple GPIO test - just blink pin 13
static void gpio_test_task(void* context) {
    UNUSED(context);
    
    // Try different pin definitions to see what works
    const GpioPin* test_pins[] = {
        &gpio_ext_pa7,  // Usually pin 13
        &gpio_ext_pa6,  // Usually pin 14
        &gpio_ext_pb3,  // Pin 5
        &gpio_ext_pb2,  // Pin 6
    };
    
    for(int pin_idx = 0; pin_idx < 4; pin_idx++) {
        // Initialize pin as output
        furi_hal_gpio_init_simple(test_pins[pin_idx], GpioModeOutputPushPull);
        
        // Blink 10 times
        for(int i = 0; i < 10; i++) {
            furi_hal_gpio_write(test_pins[pin_idx], true);
            furi_delay_ms(100);
            furi_hal_gpio_write(test_pins[pin_idx], false);
            furi_delay_ms(100);
        }
        
        // Set back to analog
        furi_hal_gpio_init_simple(test_pins[pin_idx], GpioModeAnalog);
        
        // Wait between pins
        furi_delay_ms(500);
    }
}

static bool gpio_test_back_event_callback(void* context) {
    SimpleGPIOApp* app = context;
    view_dispatcher_stop(app->view_dispatcher);
    return true;
}

static SimpleGPIOApp* gpio_test_app_alloc(void) {
    SimpleGPIOApp* app = malloc(sizeof(SimpleGPIOApp));
    
    app->gui = furi_record_open(RECORD_GUI);
    app->view_dispatcher = view_dispatcher_alloc();
    app->popup = popup_alloc();
    
    view_dispatcher_set_navigation_event_callback(app->view_dispatcher, gpio_test_back_event_callback);
    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);
    
    popup_set_header(app->popup, "GPIO Test", 64, 10, AlignCenter, AlignTop);
    popup_set_text(app->popup, "Testing GPIO pins...\nWatch Pi logs!\nPress Back when done", 64, 32, AlignCenter, AlignCenter);
    
    view_dispatcher_add_view(app->view_dispatcher, 0, popup_get_view(app->popup));
    view_dispatcher_switch_to_view(app->view_dispatcher, 0);
    
    return app;
}

static void gpio_test_app_free(SimpleGPIOApp* app) {
    view_dispatcher_remove_view(app->view_dispatcher, 0);
    popup_free(app->popup);
    view_dispatcher_free(app->view_dispatcher);
    furi_record_close(RECORD_GUI);
    free(app);
}

int32_t cec_remote_app(void* p) {
    UNUSED(p);
    
    SimpleGPIOApp* app = gpio_test_app_alloc();
    
    // Start GPIO test in background
    FuriThread* test_thread = furi_thread_alloc();
    furi_thread_set_name(test_thread, "GPIOTest");
    furi_thread_set_stack_size(test_thread, 1024);
    furi_thread_set_callback(test_thread, gpio_test_task);
    furi_thread_start(test_thread);
    
    view_dispatcher_run(app->view_dispatcher);
    
    furi_thread_free(test_thread);
    gpio_test_app_free(app);
    
    return 0;
}
