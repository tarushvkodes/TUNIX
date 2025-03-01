#!/usr/bin/python3
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

@dataclass
class PerformanceMetric:
    timestamp: float
    value: float
    threshold: float
    weight: float

class PerformanceAnalyzer:
    def __init__(self):
        self.metrics_dir = Path("/var/log/tunix/metrics")
        self.analysis_dir = Path("/var/log/tunix/analysis")
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/performance_analyzer.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        
        self.scaler = StandardScaler()
        
        # Metric weights for overall score calculation
        self.metric_weights = {
            "cpu_usage": 1.0,
            "memory_usage": 0.8,
            "io_wait": 0.7,
            "disk_usage": 0.6,
            "network_latency": 0.5,
            "temperature": 0.9
        }

    def analyze_performance(self, timespan: str = "1h") -> Dict:
        """Analyze system performance over the specified timespan"""
        try:
            # Load metrics
            metrics = self._load_metrics(timespan)
            if not metrics:
                return {}
            
            # Perform analysis
            analysis = {
                "timestamp": datetime.now().timestamp(),
                "metrics_analysis": self._analyze_metrics(metrics),
                "anomalies": self._detect_anomalies(metrics),
                "trends": self._analyze_trends(metrics),
                "recommendations": self._generate_recommendations(metrics)
            }
            
            # Save analysis results
            self._save_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing performance: {e}")
            return {}

    def _load_metrics(self, timespan: str) -> Dict:
        """Load metrics for the specified timespan"""
        try:
            # Convert timespan to seconds
            span_seconds = self._parse_timespan(timespan)
            start_time = datetime.now() - timedelta(seconds=span_seconds)
            
            metrics = {}
            for metric_file in self.metrics_dir.glob("metrics-*.json"):
                try:
                    timestamp = datetime.strptime(
                        metric_file.stem.split("-")[1],
                        "%Y%m%d-%H%M"
                    )
                    if timestamp >= start_time:
                        with open(metric_file) as f:
                            metrics[timestamp.timestamp()] = json.load(f)
                except Exception:
                    continue
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error loading metrics: {e}")
            return {}

    def _parse_timespan(self, timespan: str) -> int:
        """Convert timespan string to seconds"""
        unit = timespan[-1]
        value = int(timespan[:-1])
        
        if unit == 'h':
            return value * 3600
        elif unit == 'm':
            return value * 60
        elif unit == 'd':
            return value * 86400
        else:
            return 3600  # Default to 1 hour

    def _analyze_metrics(self, metrics: Dict) -> Dict:
        """Analyze individual metrics"""
        analysis = {}
        
        try:
            # Process each metric type
            for timestamp, data in metrics.items():
                for metric_type, value in self._extract_metrics(data).items():
                    if metric_type not in analysis:
                        analysis[metric_type] = []
                    analysis[metric_type].append(
                        PerformanceMetric(
                            timestamp=float(timestamp),
                            value=value,
                            threshold=self._get_threshold(metric_type),
                            weight=self.metric_weights.get(metric_type, 0.5)
                        )
                    )
            
            # Calculate statistics for each metric
            results = {}
            for metric_type, values in analysis.items():
                metric_values = [m.value for m in values]
                results[metric_type] = {
                    "current": metric_values[-1],
                    "mean": np.mean(metric_values),
                    "std": np.std(metric_values),
                    "min": np.min(metric_values),
                    "max": np.max(metric_values),
                    "threshold": values[0].threshold,
                    "weight": values[0].weight,
                    "threshold_violations": sum(
                        1 for m in values 
                        if m.value > m.threshold
                    )
                }
            
            return results
            
        except Exception as e:
            logging.error(f"Error analyzing metrics: {e}")
            return {}

    def _extract_metrics(self, data: Dict) -> Dict[str, float]:
        """Extract relevant metrics from raw data"""
        metrics = {}
        
        try:
            # CPU metrics
            if "cpu" in data:
                metrics["cpu_usage"] = np.mean(data["cpu"].get("usage_percent", [0]))
                metrics["io_wait"] = data["cpu"].get("iowait", 0)
            
            # Memory metrics
            if "memory" in data:
                metrics["memory_usage"] = data["memory"].get("percent", 0)
            
            # Disk metrics
            if "disk" in data:
                disk_usage = [
                    partition["percent"]
                    for partition in data["disk"].values()
                    if "percent" in partition
                ]
                if disk_usage:
                    metrics["disk_usage"] = np.mean(disk_usage)
            
            # Network metrics
            if "network" in data:
                network_errors = sum(
                    interface.get("errin", 0) + interface.get("errout", 0)
                    for interface in data["network"].values()
                )
                metrics["network_errors"] = network_errors
            
            # Temperature metrics
            if "temperature" in data:
                temp_readings = []
                for sensor in data["temperature"].values():
                    if isinstance(sensor, list):
                        for reading in sensor:
                            if isinstance(reading, dict):
                                temp_readings.append(reading.get("current", 0))
                if temp_readings:
                    metrics["temperature"] = np.max(temp_readings)
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error extracting metrics: {e}")
            return {}

    def _get_threshold(self, metric_type: str) -> float:
        """Get threshold value for a metric type"""
        thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "io_wait": 20.0,
            "disk_usage": 90.0,
            "network_errors": 100.0,
            "temperature": 80.0
        }
        return thresholds.get(metric_type, float('inf'))

    def _detect_anomalies(self, metrics: Dict) -> Dict:
        """Detect performance anomalies using Isolation Forest"""
        try:
            # Prepare data for anomaly detection
            data = []
            timestamps = []
            
            for timestamp, metric_data in metrics.items():
                feature_vector = self._create_feature_vector(metric_data)
                if feature_vector:
                    data.append(feature_vector)
                    timestamps.append(timestamp)
            
            if not data:
                return {}
            
            # Scale the data
            scaled_data = self.scaler.fit_transform(data)
            
            # Detect anomalies
            predictions = self.anomaly_detector.fit_predict(scaled_data)
            
            # Collect anomalies
            anomalies = {}
            for i, pred in enumerate(predictions):
                if pred == -1:  # Anomaly
                    timestamp = timestamps[i]
                    anomalies[timestamp] = {
                        "metrics": self._extract_metrics(metrics[timestamp]),
                        "severity": self._calculate_anomaly_severity(
                            scaled_data[i],
                            self._extract_metrics(metrics[timestamp])
                        )
                    }
            
            return anomalies
            
        except Exception as e:
            logging.error(f"Error detecting anomalies: {e}")
            return {}

    def _create_feature_vector(self, metric_data: Dict) -> List[float]:
        """Create a feature vector for anomaly detection"""
        try:
            features = []
            
            # CPU features
            if "cpu" in metric_data:
                features.extend([
                    np.mean(metric_data["cpu"].get("usage_percent", [0])),
                    metric_data["cpu"].get("iowait", 0),
                    metric_data["cpu"].get("system", 0)
                ])
            
            # Memory features
            if "memory" in metric_data:
                features.extend([
                    metric_data["memory"].get("percent", 0),
                    metric_data["memory"].get("swap_percent", 0)
                ])
            
            # Temperature feature
            if "temperature" in metric_data:
                temp_readings = []
                for sensor in metric_data["temperature"].values():
                    if isinstance(sensor, list):
                        for reading in sensor:
                            if isinstance(reading, dict):
                                temp_readings.append(reading.get("current", 0))
                if temp_readings:
                    features.append(np.max(temp_readings))
                else:
                    features.append(0)
            
            return features if features else None
            
        except Exception as e:
            logging.error(f"Error creating feature vector: {e}")
            return None

    def _calculate_anomaly_severity(self, scaled_features: np.ndarray, metrics: Dict) -> str:
        """Calculate the severity of an anomaly"""
        try:
            # Calculate distance from normal
            distance = np.linalg.norm(scaled_features)
            
            # Check threshold violations
            violations = sum(
                1 for metric, value in metrics.items()
                if value > self._get_threshold(metric)
            )
            
            # Determine severity
            if distance > 3 or violations >= 3:
                return "critical"
            elif distance > 2 or violations >= 2:
                return "high"
            else:
                return "moderate"
                
        except Exception as e:
            logging.error(f"Error calculating anomaly severity: {e}")
            return "unknown"

    def _analyze_trends(self, metrics: Dict) -> Dict:
        """Analyze performance trends"""
        trends = {}
        
        try:
            for metric_type in self.metric_weights.keys():
                values = []
                timestamps = []
                
                for timestamp, data in metrics.items():
                    extracted = self._extract_metrics(data)
                    if metric_type in extracted:
                        values.append(extracted[metric_type])
                        timestamps.append(float(timestamp))
                
                if values:
                    # Calculate trend using linear regression
                    z = np.polyfit(timestamps, values, 1)
                    trend_direction = "stable"
                    if abs(z[0]) > 0.1:  # Significant trend
                        trend_direction = "increasing" if z[0] > 0 else "decreasing"
                    
                    trends[metric_type] = {
                        "direction": trend_direction,
                        "slope": z[0],
                        "correlation": np.corrcoef(timestamps, values)[0,1]
                    }
            
            return trends
            
        except Exception as e:
            logging.error(f"Error analyzing trends: {e}")
            return {}

    def _generate_recommendations(self, metrics: Dict) -> List[Dict]:
        """Generate optimization recommendations"""
        recommendations = []
        
        try:
            analysis = self._analyze_metrics(metrics)
            
            # CPU recommendations
            if "cpu_usage" in analysis:
                cpu_stats = analysis["cpu_usage"]
                if cpu_stats["mean"] > 70:
                    recommendations.append({
                        "component": "cpu",
                        "severity": "high" if cpu_stats["mean"] > 85 else "medium",
                        "issue": "High CPU utilization",
                        "action": "Consider CPU frequency optimization or workload distribution"
                    })
            
            # Memory recommendations
            if "memory_usage" in analysis:
                mem_stats = analysis["memory_usage"]
                if mem_stats["mean"] > 80:
                    recommendations.append({
                        "component": "memory",
                        "severity": "high",
                        "issue": "High memory usage",
                        "action": "Adjust virtual memory parameters or increase swap space"
                    })
            
            # Temperature recommendations
            if "temperature" in analysis:
                temp_stats = analysis["temperature"]
                if temp_stats["max"] > 80:
                    recommendations.append({
                        "component": "thermal",
                        "severity": "high",
                        "issue": "High system temperature",
                        "action": "Review cooling system and airflow"
                    })
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Error generating recommendations: {e}")
            return []

    def _save_analysis(self, analysis: Dict):
        """Save analysis results to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M")
            analysis_file = self.analysis_dir / f"analysis-{timestamp}.json"
            
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            # Keep latest analysis in a separate file
            latest_file = self.analysis_dir / "latest_analysis.json"
            with open(latest_file, 'w') as f:
                json.dump(analysis, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving analysis: {e}")

if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.analyze_performance()