#!/usr/bin/env python3
"""
ESP32 Simulator - Simulates 5 ESP32 devices sending hit events to the shooting range backend.
This is useful for testing without actual hardware.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Optional, Any

# Try to import websockets, install if not available
try:
    import websockets
except ImportError:
    print("Installing websockets library...")
    import subprocess
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets


# Configuration
SERVER_URL = "ws://localhost:8000/ws/device/"
LANE_COUNT = 5

# Sensor positions on the target
SENSOR_POSITIONS = ["head", "chest", "stomach", "left_leg", "right_leg"]

# Points per sensor
SENSOR_POINTS = {
    "head": 100,
    "chest": 50,
    "stomach": 30,
    "left_leg": 20,
    "right_leg": 20,
}


def generate_device_id(lane_number: int) -> str:
    """Generate a device ID for a lane."""
    return f"esp32-sim-{lane_number:02d}"


def generate_hit_event(lane_number: int) -> dict:
    """Generate a random hit event."""
    position = random.choice(SENSOR_POSITIONS)
    accuracy = random.uniform(0.7, 1.0)
    raw_strength = random.randint(300, 1023)
    
    return {
        "type": "hit",
        "device_id": generate_device_id(lane_number),
        "lane": lane_number,
        "position": position,
        "accuracy": round(accuracy, 2),
        "raw_strength": raw_strength,
        "event_timestamp": datetime.utcnow().isoformat() + "Z"
    }


def generate_heartbeat(device_id: str) -> dict:
    """Generate a heartbeat message."""
    return {
        "type": "heartbeat",
        "device_id": device_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def generate_registration(lane_number: int) -> dict:
    """Generate a device registration message."""
    return {
        "type": "register_device",
        "device_id": generate_device_id(lane_number),
        "lane": lane_number,
        "sensors": SENSOR_POSITIONS,
        "firmware": "v1.0.0-simulator",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


class ESP32Simulator:
    """Simulates an ESP32 device."""
    
    def __init__(self, lane_number: int, server_url: str = SERVER_URL):
        self.lane_number = lane_number
        self.server_url = server_url
        self.device_id = generate_device_id(lane_number)
        self.websocket: Any = None
        self.is_connected = False
        self.hit_count = 0
        
    async def connect(self) -> bool:
        """Connect to the WebSocket server."""
        try:
            # Connect without authentication for development
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            print(f"[Lane {self.lane_number}] Connected to server")
            
            # Register the device
            await self.register()
            return True
        except Exception as e:
            print(f"[Lane {self.lane_number}] Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def register(self):
        """Register the device with the server."""
        if self.websocket and self.is_connected:
            reg_msg = generate_registration(self.lane_number)
            await self.websocket.send(json.dumps(reg_msg))
            print(f"[Lane {self.lane_number}] Registered as {self.device_id}")
    
    async def send_heartbeat(self):
        """Send a heartbeat message."""
        if self.websocket and self.is_connected:
            hb_msg = generate_heartbeat(self.device_id)
            await self.websocket.send(json.dumps(hb_msg))
    
    async def send_hit(self):
        """Send a random hit event."""
        if self.websocket and self.is_connected:
            hit_msg = generate_hit_event(self.lane_number)
            await self.websocket.send(json.dumps(hit_msg))
            self.hit_count += 1
            print(f"[Lane {self.lane_number}] Hit: {hit_msg['position']} (accuracy: {hit_msg['accuracy']})")
    
    async def close(self):
        """Close the connection."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print(f"[Lane {self.lane_number}] Disconnected")


async def simulate_lane(
    lane_number: int, 
    hit_interval: float = 2.0,
    heartbeat_interval: float = 5.0,
    stop_event: asyncio.Event = None
):
    """Simulate a single lane's ESP32 device."""
    if stop_event is None:
        stop_event = asyncio.Event()
    simulator = ESP32Simulator(lane_number)
    
    # Connect
    connected = await simulator.connect()
    if not connected:
        return
    
    last_heartbeat = time.time()
    
    try:
        while not stop_event.is_set():
            # Send heartbeat periodically
            current_time = time.time()
            if current_time - last_heartbeat >= heartbeat_interval:
                await simulator.send_heartbeat()
                last_heartbeat = current_time
            
            # Send random hits
            if random.random() < 0.3:  # 30% chance to hit each cycle
                await simulator.send_hit()
            
            # Wait a bit before next iteration
            await asyncio.sleep(hit_interval)
    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Lane {lane_number}] Error: {e}")
    finally:
        await simulator.close()


async def run_simulation(
    num_lanes: int = LANE_COUNT,
    hit_interval: float = 2.0,
    heartbeat_interval: float = 5.0,
    duration: Optional[float] = None
):
    """
    Run the ESP32 simulation.
    
    Args:
        num_lanes: Number of lanes to simulate
        hit_interval: Time between hit checks (seconds)
        heartbeat_interval: Time between heartbeats (seconds)
        duration: How long to run (None = forever, or seconds)
    """
    print("=" * 50)
    print("ESP32 Simulator Starting")
    print(f"Lanes: {num_lanes}")
    print(f"Server: {SERVER_URL}")
    print(f"Hit interval: {hit_interval}s")
    print(f"Heartbeat interval: {heartbeat_interval}s")
    print("=" * 50)
    
    # Create stop event
    stop_event = asyncio.Event()
    
    # Create tasks for each lane
    tasks = []
    for lane in range(1, num_lanes + 1):
        task = asyncio.create_task(
            simulate_lane(lane, hit_interval, heartbeat_interval, stop_event)
        )
        tasks.append(task)
    
    # Run for specified duration or until interrupted
    try:
        if duration:
            print(f"Running for {duration} seconds...")
            await asyncio.sleep(duration)
        else:
            print("Running until interrupted (Ctrl+C)...")
            # Wait indefinitely
            await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
    finally:
        # Stop all lanes
        stop_event.set()
        
        # Wait for all tasks to finish
        await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\nSimulation complete!")
    print(f"Total hits sent across all lanes: {sum(t.done() for t in tasks)}")


async def quick_test(num_hits: int = 10):
    """Run a quick test with a few hits."""
    print("=" * 50)
    print("ESP32 Quick Test Mode")
    print(f"Sending {num_hits} hits per lane...")
    print("=" * 50)
    
    stop_event = asyncio.Event()
    
    # Create tasks for each lane
    tasks = []
    for lane in range(1, LANE_COUNT + 1):
        task = asyncio.create_task(
            simulate_lane(lane, hit_interval=0.5, heartbeat_interval=30, stop_event=stop_event)
        )
        tasks.append(task)
    
    # Wait for some hits
    await asyncio.sleep(num_hits * 0.5)
    
    # Stop
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\nQuick test complete!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ESP32 Simulator for Shooting Range")
    parser.add_argument("-n", "--lanes", type=int, default=LANE_COUNT, help="Number of lanes to simulate")
    parser.add_argument("-i", "--hit-interval", type=float, default=2.0, help="Time between hit checks (seconds)")
    parser.add_argument("-hb", "--heartbeat-interval", type=float, default=5.0, help="Time between heartbeats (seconds)")
    parser.add_argument("-d", "--duration", type=float, help="Duration to run (seconds)")
    parser.add_argument("-q", "--quick", action="store_true", help="Quick test mode (10 hits)")
    parser.add_argument("-u", "--url", type=str, default=SERVER_URL, help="WebSocket server URL")
    
    args = parser.parse_args()
    
    # Update global server URL
    global SERVER_URL
    SERVER_URL = args.url
    
    if args.quick:
        asyncio.run(quick_test())
    else:
        asyncio.run(run_simulation(
            num_lanes=args.lanes,
            hit_interval=args.hit_interval,
            heartbeat_interval=args.heartbeat_interval,
            duration=args.duration
        ))


if __name__ == "__main__":
    main()
