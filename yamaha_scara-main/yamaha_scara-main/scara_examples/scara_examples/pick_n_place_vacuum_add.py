#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from std_srvs.srv import SetBool
from yk400xe_interfaces.srv import MoveTrajectory
from yk400xe_interfaces.msg import Move
from geometry_msgs.msg import PoseStamped

import time
import threading
import numpy as np

class PickAndPlaceVacuum(Node):
    def __init__(self):
        super().__init__("pick_n_place_vacuum_node")

        self.lock = threading.Lock()

        self.ef_ = []

        self.home_pose_ = []
        self.pick_pose_ = []
        self.place_pose_ = []


        self.ef_sub_ = self.create_subscription(
            PoseStamped,
            "/ef_state",
            self.ef_state_cb,
            10)


        self.move_client_ = self.create_client(
            MoveTrajectory,
            "/command/move",
        )
        while not self.move_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Vacuum control service not available, trying again")


        self.vacuum_client_ = self.create_client(
            SetBool,
            "/set_vacuum",
        )
        while not self.vacuum_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Vacuum control service not available, trying again")

        self.set_vacuum(False)
        
        while len(self.ef_) == 0:
            rclpy.spin_once(self)

        self.input_thread = threading.Thread(target=self.run, daemon=True)
        self.input_thread.start()


    def ef_state_cb(self,msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z

        self.ef_ = [x,y,z,0]


    def input_loop(self):
        while True:
            input("Press any key")
            with self.lock:
                print(f"ef {self.ef_}")

    # -------------------------------------------------------------------------
    def set_pose(self):
        
        with self.lock:
            # home_pose
            self.home_pose_ = [6.277, 315.247, 26.196, 0.0]
            
            # pick_pose
            self.pick_pose_ = [16.525, 320.888, 152.813, 0.0]
            
            # place_pose
            self.place_pose_ = [-161.714, 255/469, 98.259, 0.0]
            
        print("\nI can check point")
    # -----------------------------------------------------------------------------


    def is_at(self,pose,eps=0.01):
        with self.lock:
            d = np.linalg.norm(np.array(pose[:3]) - np.array(self.ef_[:3]))
        return(d<eps)


    def go_to(self,pose,arch=True):
        move_request = MoveTrajectory.Request()

        move_msg = Move()
        move_msg.pose = pose
        move_msg.do_arch = arch
        move_msg.arch = [0,0,0]
        move_msg.speed = 10
        move_msg.coords_type = 0  # Std Coordinates
        move_msg.move_type = 1  # P
        move_msg.wait_arm = False

        move_request.move_cmds = [move_msg]
        self.future = self.move_client_.call_async(move_request)


    def set_vacuum(self,state):
        vacuum_request = SetBool.Request()

        vacuum_request.data = state

        self.future = self.vacuum_client_.call_async(vacuum_request)
        return
    
    
    def run(self):
        self.set_pose()

        self.get_logger().info(f"Home {self.home_pose_}")
        self.get_logger().info(f"Pick {self.pick_pose_}")
        self.get_logger().info(f"Place {self.place_pose_}")

        while(True):
            input("press ENTER to start")

            self.go_to(self.home_pose_,arch=False)
            while(not self.is_at(self.home_pose_)):
                time.sleep(0.01)

            time.sleep(0.1)
            self.go_to(self.pick_pose_)
            while(not self.is_at(self.pick_pose_)):
                time.sleep(0.01)
            

            self.set_vacuum(True)
            time.sleep(0.2)

            time.sleep(0.1)
            self.go_to(self.place_pose_)
            while(not self.is_at(self.place_pose_)):
                time.sleep(0.01)
            
            self.set_vacuum(False)
            time.sleep(0.2)

            time.sleep(0.1)
            self.go_to(self.home_pose_,arch=False)
            while(not self.is_at(self.home_pose_)):
                time.sleep(0.01)
            time.sleep(1)


def main(args=None):
    rclpy.init(args=args)

    node = PickAndPlaceVacuum()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.set_vacuum(False)
        node.destroy_node()
        rclpy.shutdown()
    

if __name__ == "__main__":
    main()