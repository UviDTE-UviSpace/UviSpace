//file: avalon_camera.hpp
//It the avalon_camera component

#ifndef __AVALON_CAMERA_H
#define __AVALON_CAMERA_H

#include <inttypes.h>//for uint16_t
#include <string.h>//for memcpy
#include <iostream>
#include <stdexcept>

/*
Macros for accessing an address map with a data bus size of 8, 16 or 32 bits.
*/
#ifndef __LOW_LEVEL_RW_MACROS
#define __LOW_LEVEL_RW_MACROS
// Macro for R/W operations on 8-bit addresses.
#define IOWR8(base, offset, dat)        (*((uint8_t*)base + offset) = (uint8_t)dat)
#define IORD8(base, offset)             (*((uint8_t*)base + offset))
// Macro for R/W operations on 16-bit addresses.
#define IOWR16(base, offset, dat)       ((* ((uint32_t*)((uint8_t*)base + offset*2))) = (uint16_t)dat)
#define IORD16(base, offset)            (* ((uint32_t*)((uint8_t)base + offset*2)))
// Macro for R/W operations on 16-bit addresses.
#define IOWR32(base, offset, dat)       ((* ((uint32_t*)((uint8_t*)base + offset*4))) = (uint32_t)dat)
#define IORD32(base, offset)            (* ((uint32_t*)((uint8_t*)base + offset*4)))
#endif

/*
Internal address map of avalon camera (32-bit addresses)
*/
// registers to control image_capture component
#define CAMERA_START_CAPTURE           0x00
#define CAMERA_CAPTURE_WIDTH           0x01
#define CAMERA_CAPTURE_HEIGHT          0x02
#define CAMERA_BUFF0                   0x03
#define CAMERA_BUFF1                   0x04
#define CAMERA_BUFF0_FULL              0x05
#define CAMERA_BUFF1_FULL              0x06
#define CAMERA_CAPTURE_STANDBY         0x07
// registers to control camera_config component
#define ADDR_WIDTH                     0x09
#define ADDR_HEIGHT                    0x0a
#define ADDR_START_ROW                 0x0b
#define ADDR_START_COLUMN              0x0c
#define ADDR_ROW_SIZE                  0x0d
#define ADDR_COLUMN_SIZE               0x0e
#define ADDR_ROW_MODE                  0x0f
#define ADDR_COLUMN_MODE               0x10
#define ADDR_EXPOSURE                  0x11
// soft_reset signal
#define CAMERA_SOFT_RESET              0x1f

/*
Default values of some config registers
*/
#define CONFIG_WIDTH_DEFAULT                     640
#define CONFIG_HEIGHT_DEFAULT                    480
#define CONFIG_START_ROW_DEFAULT                 0
#define CONFIG_START_COLUMN_DEFAULT              0
#define CONFIG_ROW_SIZE_DEFAULT                  1919
#define CONFIG_COLUMN_SIZE_DEFAULT               2559
#define CONFIG_ROW_MODE_DEFAULT                  1
#define CONFIG_COLUMN_MODE_DEFAULT               17
#define CONFIG_EXPOSURE_DEFAULT                  1023

/*
Camera capture error codes
*/
#define CAMERA_NO_REPLY 1
#define CAMERA_CAPTURE_GET_LINE_BUFFER_FULL_NO_WAIT 2
#define CAMERA_CAPTURE_GET_LINE_TIMEOUT 3

/*
Number of lines to acquire in one buffer
*/
#define LINES_PER_BUFF 8

/*
Struct to help the acquisition of the image
*/
// Size in bits of a color component (R,G,B or Gray)
// We have settled in a 8 bit component, in case a 16 bit component was required, the typedef should be
// changed to uint16_t.
typedef uint8_t color_component;

//format of a captured pixel
typedef struct cpixel_ {
    color_component R;
    color_component G;
    color_component B;
    color_component Gray;
} cpixel;

/*
Class definition for easy control of the camera
*/
class avalon_camera {
private: //accesible only inside the class
    //--Class Variables--//
    //Virtual base address of the avalon_camera. Filled in the constructor
    void* address;

    //Size of the image in pixels (screen pixels.
    //dont missunderstand with cam pixels that are usually double)
    //Filled each time set_width and set_height are called
    uint16_t img_width;
    uint16_t img_height;

    //virtual addresses of the buffers where images are captured.
    //virtual and physical addresses of the buffer that connects
    //hardware. Used to save lines of the image
    void* buff_v;
    void* buff_p;
    cpixel* buff0_v; //pointer inside buff_v, to save odd lines
    cpixel* buff1_v; //pointer inside buff_v, to save even lines
    //current_buff_v is sometimes buff0_v, sometimes buff1_v, depending
    //on the image line currently being acquired
    cpixel* current_buff_v;

public: //accessible from outside the class
    //--Class Methods definition--//
    //constructor
	avalon_camera(void* virtual_address);

    //methods to set the camera configuration
    //the following methods change the values of the avalon_camera
    //registers without resetting the camera. So after using this
    //functions call config_update to reset the camera with the
    //new parameters and actually change the camera behaviour.
    uint16_t get_width();
    void set_width(uint16_t val);

    uint16_t get_height();
    void set_height(uint16_t val);

    uint16_t get_start_row();
    void set_start_row(uint16_t val);

    uint16_t get_start_column();
    void set_start_column(uint16_t val);

    uint16_t get_row_size();
    void set_row_size(uint16_t val);

    uint16_t get_column_size();
    void set_column_size(uint16_t val);

    uint16_t get_row_mode();
    void set_row_mode(uint16_t val);

    uint16_t get_column_mode();
    void set_column_mode(uint16_t val);

    uint16_t get_exposure();
    void set_exposure(uint16_t val);

    void set_default_configuration();
    //config_update loads new configuration into the camera and resets
    //the video stream.
    void config_update();

    //methods to capture an image into the processor
    void capture_set_buffer(void* buffer_v, void* buffer_p);
    void capture_image(cpixel* image);
private:
    void capture_start();
    void capture_get_line(cpixel*& line);
    //resets and removes soft reset to reset the video stream
    //it is private. not intended to be used by the user yet
    int reset();
};
namespace exception {
    class camera_no_reply : public std::runtime_error {
    public:
        camera_no_reply() : std::runtime_error("camera_no_reply") {}
    };
    class capture_buffer_full : public std::runtime_error {
    public:
        capture_buffer_full() : std::runtime_error("capture_buffer_full") {}
    };
    class capture_timeout : public std::runtime_error {
    public:
        capture_timeout() : std::runtime_error("capture_timeout") {}
    };
}


#endif //__AVALON_CAMERA_H
