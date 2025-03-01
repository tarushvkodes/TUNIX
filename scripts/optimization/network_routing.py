#!/usr/bin/python3
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class NetworkRouteOptimizer:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/network/routing")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/network_routing.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def optimize_routes(self):
        """Optimize network routes based on latency and bandwidth"""
        try:
            # Get current routes
            routes = self._get_current_routes()
            
            # Measure performance for each route
            route_metrics = self._measure_route_performance(routes)
            
            # Apply optimizations
            self._apply_route_optimizations(route_metrics)
            
        except Exception as e:
            logging.error(f"Error optimizing routes: {e}")

    def _get_current_routes(self) -> List[Dict]:
        """Get current routing table"""
        routes = []
        try:
            result = subprocess.run(["ip", "-j", "route"], capture_output=True, text=True)
            if result.returncode == 0:
                routes = json.loads(result.stdout)
        except Exception as e:
            logging.error(f"Error getting routes: {e}")
        return routes

    def _measure_route_performance(self, routes: List[Dict]) -> List[Dict]:
        """Measure performance metrics for each route"""
        route_metrics = []
        
        for route in routes:
            if "gateway" not in route:
                continue
                
            metrics = {
                "route": route,
                "latency": self._measure_latency(route["gateway"]),
                "bandwidth": self._measure_bandwidth(route["gateway"]),
                "packet_loss": self._measure_packet_loss(route["gateway"])
            }
            route_metrics.append(metrics)
            
        return route_metrics

    def _measure_latency(self, target: str) -> Optional[float]:
        """Measure latency to target"""
        try:
            result = subprocess.run(
                ["ping", "-c", "3", "-q", target],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract average RTT
                for line in result.stdout.split("\n"):
                    if "rtt min/avg/max" in line:
                        avg = float(line.split("/")[4])
                        return avg
        except Exception as e:
            logging.error(f"Error measuring latency to {target}: {e}")
        return None

    def _measure_bandwidth(self, target: str) -> Optional[float]:
        """Estimate available bandwidth to target"""
        try:
            # Send 5 large pings to estimate bandwidth
            result = subprocess.run(
                ["ping", "-c", "5", "-s", "1472", target],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Calculate rough bandwidth from timing
                for line in result.stdout.split("\n"):
                    if "rtt min/avg/max" in line:
                        # Very rough estimate based on ping times
                        rtt = float(line.split("/")[4])
                        return (1472 * 8) / (rtt / 1000) # bits per second
        except Exception as e:
            logging.error(f"Error measuring bandwidth to {target}: {e}")
        return None

    def _measure_packet_loss(self, target: str) -> Optional[float]:
        """Measure packet loss percentage to target"""
        try:
            result = subprocess.run(
                ["ping", "-c", "10", "-q", target],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "packet loss" in line:
                        return float(line.split("%")[0].split()[-1])
        except Exception as e:
            logging.error(f"Error measuring packet loss to {target}: {e}")
        return None

    def _apply_route_optimizations(self, route_metrics: List[Dict]):
        """Apply route optimizations based on measured metrics"""
        try:
            # Sort routes by performance score
            scored_routes = self._score_routes(route_metrics)
            
            # Apply optimizations
            for route in scored_routes:
                if route["score"] < 0.5:  # Poor performing route
                    self._optimize_poor_route(route)
                else:
                    self._optimize_good_route(route)
                    
        except Exception as e:
            logging.error(f"Error applying route optimizations: {e}")

    def _score_routes(self, route_metrics: List[Dict]) -> List[Dict]:
        """Score routes based on their performance metrics"""
        scored_routes = []
        
        for metrics in route_metrics:
            score = 0.0
            count = 0
            
            # Latency score (lower is better)
            if metrics["latency"] is not None:
                score += max(0, 1 - (metrics["latency"] / 1000))
                count += 1
                
            # Bandwidth score (higher is better)
            if metrics["bandwidth"] is not None:
                score += min(1, metrics["bandwidth"] / 1000000)  # Normalize to Mbps
                count += 1
                
            # Packet loss score (lower is better)
            if metrics["packet_loss"] is not None:
                score += max(0, 1 - (metrics["packet_loss"] / 100))
                count += 1
                
            if count > 0:
                metrics["score"] = score / count
                scored_routes.append(metrics)
                
        return sorted(scored_routes, key=lambda x: x["score"], reverse=True)

    def _optimize_poor_route(self, route: Dict):
        """Apply optimizations for poorly performing routes"""
        try:
            gateway = route["route"]["gateway"]
            dev = route["route"].get("dev", "")
            
            # Add latency-based metrics
            subprocess.run([
                "ip", "route", "change",
                route["route"]["dst"], "via", gateway,
                "dev", dev, "metric", "100"
            ])
            
            # Enable multipath routing if available
            if self._check_multipath_support():
                self._enable_multipath_routing(route["route"])
                
        except Exception as e:
            logging.error(f"Error optimizing poor route: {e}")

    def _optimize_good_route(self, route: Dict):
        """Apply optimizations for well-performing routes"""
        try:
            gateway = route["route"]["gateway"]
            dev = route["route"].get("dev", "")
            
            # Set lower metric for better routes
            subprocess.run([
                "ip", "route", "change",
                route["route"]["dst"], "via", gateway,
                "dev", dev, "metric", "10"
            ])
            
        except Exception as e:
            logging.error(f"Error optimizing good route: {e}")

    def _check_multipath_support(self) -> bool:
        """Check if kernel supports multipath routing"""
        try:
            with open("/proc/sys/net/ipv4/fib_multipath_use_neigh") as f:
                return f.read().strip() == "1"
        except:
            return False

    def _enable_multipath_routing(self, route: Dict):
        """Enable multipath routing for a route"""
        try:
            # Enable multipath load balancing
            with open("/proc/sys/net/ipv4/fib_multipath_use_neigh", "w") as f:
                f.write("1")
                
            # Configure multipath route
            subprocess.run([
                "ip", "route", "add",
                route["dst"], "via", route["gateway"],
                "dev", route.get("dev", ""),
                "metric", "100",
                "multipath"
            ])
            
        except Exception as e:
            logging.error(f"Error enabling multipath routing: {e}")

    def monitor_routes(self):
        """Continuously monitor and optimize routes"""
        while True:
            try:
                self.optimize_routes()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logging.error(f"Error in route monitoring: {e}")
                time.sleep(60)

if __name__ == "__main__":
    optimizer = NetworkRouteOptimizer()
    optimizer.monitor_routes()