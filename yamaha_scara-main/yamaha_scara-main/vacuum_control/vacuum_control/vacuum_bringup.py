#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from std_srvs.srv import SetBool

import serial, threading

class VacuumController(Node):
    def __init__(self):
        super().__init__("vacuum_controller_node")

        # self.ser_ = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        self.vacuum_state_ = 0 # Useless for now, could be published in the future

        self.service_server_ = self.create_service(
            SetBool,
            "set_vacuum",
            self.request_callback
        )

        self.input_thread_ = threading.Thread(target=self.terminal_input_loop)
        self.input_thread_.daemon = True
        self.input_thread_.start()

        self.get_logger().info("Node started")

    
    # def close_ser(self):
    #     self.ser_.write(b'0')
    #     self.ser_.close()
    #     return 

    def request_callback(self, request, response):
        # if request.data:
        #     self.ser_.write(b'1')
        #     self.vacuum_state_ = 1
        #     response.success = True
        #     response.message = "Vacuum ON"
        # else:
        #     self.ser_.write(b'0')
        #     self.vacuum_state_ = 0
        #     response.success = True
        #     response.message = "Vacuum OFF"

        return response
    
    def terminal_input_loop(self):
        while True:
            try:
                cmd = input(" 0 (OFF) or 1 (ON): ").strip()

                if cmd == '1':
                    # self.ser_.write(b'1')
                    self.vacuum_state_ = 1
                    print("Vacuum ON")

                elif cmd == '0':
                    # self.ser_.write(b'0')
                    self.vacuum_state_ = 0
                    print("Vacuum OFF")

                else:
                    print("Wrong input")

            except KeyboardInterrupt:
                break

def main(args=None):
    rclpy.init(args=args)

    node = VacuumController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # node.close_ser()
        node.destroy_node()
        rclpy.shutdown()
    

if __name__ == "__main__":
    main()