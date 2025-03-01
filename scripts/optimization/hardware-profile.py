#!/usr/bin/python3

import subprocess
import json
import os
import sys
import argparse
from typing import Dict, List, Optional

class HardwareProfiler:
    def __init__(self):
        self.profile_data = {}
        self.optimizations = {}
        self.config_dir = "/etc/tunix/hardware-profiles"
        
    def collect_cpu_info(self) -> Dict:
        """Collect CPU information and determine optimal settings"""
        cpu_info = {}
        
        with open("/proc/cpuinfo", "r") as f:
            content = f.read()
            
        # Get CPU model and core count
        cpu_info["model"] = [l for l in content.split("\n") if "model name" in l][0].split(":")[1].strip()
        cpu_info["cores"] = len([l for l in content.split("\n") if "processor" in l])
        
        # Determine CPU scaling governor
        if "amd" in cpu_info["model"].lower():
            cpu_info["governor"] = "ondemand"
        elif "intel" in cpu_info["model"].lower():
            cpu_info["governor"] = "powersave"
        else:
            cpu_info["governor"] = "schedutil"
            
        return cpu_info
    
    def collect_gpu_info(self) -> Dict:
        """Collect GPU information and optimal configurations"""
        gpu_info = {}
        
        try:
            lspci = subprocess.run(["lspci", "-nn"], capture_output=True, text=True)
            gpu_lines = [l for l in lspci.stdout.split("\n") if "VGA" in l or "3D" in l]
            
            for line in gpu_lines:
                if "NVIDIA" in line:
                    gpu_info["type"] = "nvidia"
                    gpu_info["power_management"] = "performance"
                elif "AMD" in line:
                    gpu_info["type"] = "amd"
                    gpu_info["power_management"] = "dpm-balanced"
                elif "Intel" in line:
                    gpu_info["type"] = "intel"
                    gpu_info["power_management"] = "balanced"
                    
        except Exception as e:
            gpu_info["error"] = str(e)
            
        return gpu_info
    
    def collect_memory_info(self) -> Dict:
        """Analyze system memory and determine optimal settings"""
        mem_info = {}
        
        with open("/proc/meminfo", "r") as f:
            content = f.read()
            
        # Get total memory
        total_mem = int([l for l in content.split("\n") if "MemTotal" in l][0].split()[1])
        mem_info["total"] = total_mem // 1024  # Convert to MB
        
        # Calculate optimal swap
        if mem_info["total"] <= 4096:  # 4GB or less
            mem_info["swap"] = mem_info["total"] * 2
        elif mem_info["total"] <= 16384:  # 16GB or less
            mem_info["swap"] = mem_info["total"]
        else:
            mem_info["swap"] = 16384  # Cap at 16GB
            
        # Calculate optimal values
        mem_info["vm.swappiness"] = 10 if mem_info["total"] >= 8192 else 60
        mem_info["vm.vfs_cache_pressure"] = 50
        mem_info["vm.dirty_ratio"] = 10
        mem_info["vm.dirty_background_ratio"] = 5
        
        return mem_info
    
    def collect_storage_info(self) -> Dict:
        """Analyze storage devices and determine optimal settings"""
        storage_info = {}
        
        try:
            lsblk = subprocess.run(["lsblk", "-d", "-o", "NAME,ROTA,SIZE,MODEL"], 
                                 capture_output=True, text=True)
            
            for line in lsblk.stdout.split("\n")[1:]:  # Skip header
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    dev_name = parts[0]
                    is_rotational = parts[1] == "1"
                    
                    storage_info[dev_name] = {
                        "rotational": is_rotational,
                        "scheduler": "bfq" if is_rotational else "none",
                        "read_ahead": 2048 if is_rotational else 256,
                        "disk_type": "hdd" if is_rotational else "ssd"
                    }
                    
        except Exception as e:
            storage_info["error"] = str(e)
            
        return storage_info
    
    def generate_optimizations(self):
        """Generate optimization recommendations based on hardware profile"""
        self.profile_data = {
            "cpu": self.collect_cpu_info(),
            "gpu": self.collect_gpu_info(),
            "memory": self.collect_memory_info(),
            "storage": self.collect_storage_info()
        }
        
        # CPU optimizations
        self.optimizations["cpu"] = [
            f"cpupower frequency-set -g {self.profile_data['cpu']['governor']}",
            "systemctl enable thermald"
        ]
        
        # GPU optimizations
        if self.profile_data["gpu"].get("type") == "nvidia":
            self.optimizations["gpu"] = [
                "nvidia-settings -a [gpu:0]/GpuPowerMizerMode=1",
                "nvidia-settings -a [gpu:0]/GPUFanControlState=1"
            ]
        elif self.profile_data["gpu"].get("type") == "amd":
            self.optimizations["gpu"] = [
                f"echo {self.profile_data['gpu']['power_management']} > /sys/class/drm/card0/device/power_dpm_state"
            ]
        
        # Memory optimizations
        self.optimizations["memory"] = [
            f"sysctl -w vm.swappiness={self.profile_data['memory']['vm.swappiness']}",
            f"sysctl -w vm.vfs_cache_pressure={self.profile_data['memory']['vm.vfs_cache_pressure']}",
            f"sysctl -w vm.dirty_ratio={self.profile_data['memory']['vm.dirty_ratio']}",
            f"sysctl -w vm.dirty_background_ratio={self.profile_data['memory']['vm.dirty_background_ratio']}"
        ]
        
        # Storage optimizations
        self.optimizations["storage"] = []
        for dev, info in self.profile_data["storage"].items():
            if isinstance(info, dict):  # Skip error entries
                self.optimizations["storage"].extend([
                    f"echo {info['scheduler']} > /sys/block/{dev}/queue/scheduler",
                    f"echo {info['read_ahead']} > /sys/block/{dev}/queue/read_ahead_kb"
                ])
    
    def apply_optimizations(self):
        """Apply the optimizations to the system"""
        if os.geteuid() != 0:
            raise PermissionError("Must run as root to apply optimizations")
            
        success = True
        for category, commands in self.optimizations.items():
            for cmd in commands:
                try:
                    subprocess.run(cmd, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error applying {category} optimization: {e}", file=sys.stderr)
                    success = False
                    
        # Save applied profile
        os.makedirs(self.config_dir, exist_ok=True)
        with open(f"{self.config_dir}/current-profile.json", "w") as f:
            json.dump({
                "profile": self.profile_data,
                "optimizations": self.optimizations
            }, f, indent=2)
            
        return success
    
    def save_profile(self, name: str):
        """Save current profile with a specific name"""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(f"{self.config_dir}/{name}.json", "w") as f:
            json.dump({
                "profile": self.profile_data,
                "optimizations": self.optimizations
            }, f, indent=2)
            
    def load_profile(self, name: str) -> bool:
        """Load and apply a saved profile"""
        try:
            with open(f"{self.config_dir}/{name}.json", "r") as f:
                data = json.load(f)
                self.profile_data = data["profile"]
                self.optimizations = data["optimizations"]
                return self.apply_optimizations()
        except FileNotFoundError:
            print(f"Profile {name} not found", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error loading profile: {e}", file=sys.stderr)
            return False

def main():
    parser = argparse.ArgumentParser(description="TUNIX Hardware Profiler and Optimizer")
    parser.add_argument("--analyze", action="store_true", help="Analyze hardware only")
    parser.add_argument("--apply", action="store_true", help="Apply optimizations")
    parser.add_argument("--save", metavar="NAME", help="Save profile with name")
    parser.add_argument("--load", metavar="NAME", help="Load and apply saved profile")
    
    args = parser.parse_args()
    
    profiler = HardwareProfiler()
    
    if args.analyze:
        profiler.generate_optimizations()
        print(json.dumps(profiler.profile_data, indent=2))
    elif args.save:
        profiler.generate_optimizations()
        profiler.save_profile(args.save)
        print(f"Profile saved as {args.save}")
    elif args.load:
        if profiler.load_profile(args.load):
            print(f"Successfully loaded and applied profile {args.load}")
        else:
            sys.exit(1)
    elif args.apply:
        profiler.generate_optimizations()
        if profiler.apply_optimizations():
            print("Successfully applied optimizations")
        else:
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()