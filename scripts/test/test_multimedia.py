#!/usr/bin/python3

import subprocess
import json
import os
import tempfile
from typing import Dict, List, Tuple

class MultimediaTest:
    def __init__(self):
        self.test_files = {
            'video': {
                'h264': 'test_h264.mp4',
                'h265': 'test_h265.mp4',
                'vp9': 'test_vp9.webm',
                'av1': 'test_av1.mkv'
            },
            'audio': {
                'mp3': 'test_mp3.mp3',
                'aac': 'test_aac.m4a',
                'opus': 'test_opus.opus',
                'flac': 'test_flac.flac'
            },
            'image': {
                'jpg': 'test_jpg.jpg',
                'png': 'test_png.png',
                'webp': 'test_webp.webp',
                'heif': 'test_heif.heif'
            }
        }

    def run_tests(self) -> Dict:
        """Run all multimedia tests and return results"""
        results = {
            'hardware_acceleration': self._test_hw_acceleration(),
            'codec_support': self._test_codec_support(),
            'audio_system': self._test_audio_system(),
            'image_processing': self._test_image_processing(),
            'overall_status': 'pass'
        }
        
        # Determine overall status
        if any(not result['status'] for result in results.values() if isinstance(result, dict)):
            results['overall_status'] = 'fail'
        
        return results

    def _test_hw_acceleration(self) -> Dict:
        """Test hardware acceleration capabilities"""
        result = {
            'status': True,
            'vaapi': False,
            'vdpau': False,
            'errors': []
        }

        # Test VA-API
        try:
            vainfo = subprocess.run(['vainfo'], capture_output=True, text=True)
            if 'VA-API version' in vainfo.stdout:
                result['vaapi'] = True
            else:
                result['errors'].append('VA-API not working properly')
                result['status'] = False
        except FileNotFoundError:
            result['errors'].append('VA-API tools not installed')
            result['status'] = False

        # Test VDPAU
        try:
            vdpauinfo = subprocess.run(['vdpauinfo'], capture_output=True, text=True)
            if 'VDPAU Driver' in vdpauinfo.stdout:
                result['vdpau'] = True
            else:
                result['errors'].append('VDPAU not working properly')
                result['status'] = False
        except FileNotFoundError:
            result['errors'].append('VDPAU tools not installed')
            result['status'] = False

        return result

    def _test_codec_support(self) -> Dict:
        """Test codec support for various formats"""
        result = {
            'status': True,
            'supported_codecs': [],
            'unsupported_codecs': [],
            'errors': []
        }

        # Create test files
        with tempfile.TemporaryDirectory() as tmpdir:
            for format_type, formats in self.test_files.items():
                for codec, filename in formats.items():
                    filepath = os.path.join(tmpdir, filename)
                    if self._create_test_file(filepath, format_type, codec):
                        result['supported_codecs'].append(codec)
                    else:
                        result['unsupported_codecs'].append(codec)
                        result['status'] = False

        return result

    def _test_audio_system(self) -> Dict:
        """Test audio system functionality"""
        result = {
            'status': True,
            'backend': None,
            'devices': [],
            'errors': []
        }

        # Check audio backend
        if subprocess.run(['pidof', 'pipewire'], capture_output=True).returncode == 0:
            result['backend'] = 'pipewire'
        elif subprocess.run(['pidof', 'pulseaudio'], capture_output=True).returncode == 0:
            result['backend'] = 'pulseaudio'
        else:
            result['errors'].append('No audio backend running')
            result['status'] = False

        # Test audio output
        try:
            # Generate test tone
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=1',
                '-f', 'pulse', 'default'
            ], capture_output=True)
        except Exception as e:
            result['errors'].append(f'Audio output test failed: {str(e)}')
            result['status'] = False

        # Get device list
        try:
            pactl = subprocess.run(['pactl', 'list'], capture_output=True, text=True)
            result['devices'] = [
                line.split('Name: ')[1].strip()
                for line in pactl.stdout.split('\n')
                if 'Name: ' in line
            ]
        except Exception as e:
            result['errors'].append(f'Device enumeration failed: {str(e)}')
            result['status'] = False

        return result

    def _test_image_processing(self) -> Dict:
        """Test image processing capabilities"""
        result = {
            'status': True,
            'supported_formats': [],
            'conversion_tests': {},
            'errors': []
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test format support
            for img_format in ['jpg', 'png', 'webp', 'heif']:
                test_file = os.path.join(tmpdir, f'test.{img_format}')
                if self._create_test_image(test_file, img_format):
                    result['supported_formats'].append(img_format)
                else:
                    result['errors'].append(f'{img_format} format not supported')
                    result['status'] = False

            # Test format conversion
            for src_fmt in result['supported_formats']:
                for dst_fmt in result['supported_formats']:
                    if src_fmt != dst_fmt:
                        success = self._test_image_conversion(
                            os.path.join(tmpdir, f'test.{src_fmt}'),
                            os.path.join(tmpdir, f'converted.{dst_fmt}')
                        )
                        result['conversion_tests'][f'{src_fmt}->{dst_fmt}'] = success
                        if not success:
                            result['errors'].append(f'Conversion {src_fmt}->{dst_fmt} failed')
                            result['status'] = False

        return result

    def _create_test_file(self, filepath: str, format_type: str, codec: str) -> bool:
        """Create a test media file for the given format"""
        try:
            if format_type == 'video':
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=30',
                    '-c:v', codec, filepath
                ], capture_output=True)
            elif format_type == 'audio':
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=1',
                    '-c:a', codec, filepath
                ], capture_output=True)
            return True
        except Exception:
            return False

    def _create_test_image(self, filepath: str, img_format: str) -> bool:
        """Create a test image in the specified format"""
        try:
            subprocess.run([
                'convert', '-size', '100x100', 'xc:white',
                '-draw', 'circle 50,50 50,1', filepath
            ], capture_output=True)
            return True
        except Exception:
            return False

    def _test_image_conversion(self, src: str, dst: str) -> bool:
        """Test image format conversion"""
        try:
            subprocess.run(['convert', src, dst], capture_output=True)
            return True
        except Exception:
            return False

def main():
    tester = MultimediaTest()
    results = tester.run_tests()
    
    # Print results in a readable format
    print("\nTUNIX Multimedia Test Results")
    print("=============================")
    
    for category, result in results.items():
        if category != 'overall_status':
            print(f"\n{category.replace('_', ' ').title()}:")
            if isinstance(result, dict):
                for key, value in result.items():
                    if key != 'errors':
                        print(f"  {key}: {value}")
                if result.get('errors'):
                    print("  Errors:")
                    for error in result['errors']:
                        print(f"    - {error}")
    
    print(f"\nOverall Status: {results['overall_status'].upper()}")

if __name__ == "__main__":
    main()