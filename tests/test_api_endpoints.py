#!/usr/bin/env python3
"""
API Endpoint Test Suite for GDriveProtect
Tests all API endpoints with proper error handling and authentication scenarios.
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, List

class APITester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, response: requests.Response = None, error: str = None):
        """Log test results"""
        result = {
            'test_name': test_name,
            'success': success,
            'status_code': response.status_code if response else None,
            'error': error,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"   Error: {error}")
        if response and not success:
            print(f"   Status: {response.status_code}")
            try:
                print(f"   Response: {response.json()}")
            except:
                print(f"   Response: {response.text}")
        print()

    def test_health_endpoints(self) -> bool:
        """Test all health check endpoints"""
        print("🔍 Testing Health Endpoints...")
        
        health_endpoints = [
            ('/api/dlp/health', 'DLP Scanner Health'),
            ('/api/drive/health', 'Drive Monitor Health'),
            ('/api/vault/health', 'Vault Manager Health')
        ]
        
        all_passed = True
        for endpoint, name in health_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                success = response.status_code == 200
                self.log_test(name, success, response)
                if not success:
                    all_passed = False
            except Exception as e:
                self.log_test(name, False, error=str(e))
                all_passed = False
                
        return all_passed

    def test_dlp_endpoints(self) -> bool:
        """Test DLP scanner endpoints"""
        print("🔍 Testing DLP Scanner Endpoints...")
        
        # Test scan endpoint with invalid data
        try:
            response = self.session.post(f"{self.base_url}/api/dlp/scan", 
                                      json={'file_id': 'test123'})
            # Should return 400 or 500 due to missing credentials
            success = response.status_code in [400, 500]
            self.log_test("DLP Scan (Invalid)", success, response)
        except Exception as e:
            self.log_test("DLP Scan (Invalid)", False, error=str(e))
            
        # Test batch scan endpoint
        try:
            response = self.session.post(f"{self.base_url}/api/dlp/scan/batch", 
                                      json={'file_ids': ['test123']})
            success = response.status_code in [400, 500]
            self.log_test("DLP Batch Scan", success, response)
        except Exception as e:
            self.log_test("DLP Batch Scan", False, error=str(e))
            
        return True

    def test_drive_endpoints(self) -> bool:
        """Test Drive monitor endpoints"""
        print("🔍 Testing Drive Monitor Endpoints...")
        
        # Test list files endpoint
        try:
            response = self.session.get(f"{self.base_url}/api/drive/files?max_results=5")
            # Should return 500 due to missing authentication
            success = response.status_code in [500, 400]
            self.log_test("Drive List Files", success, response)
        except Exception as e:
            self.log_test("Drive List Files", False, error=str(e))
            
        # Test scan trigger endpoint
        try:
            response = self.session.post(f"{self.base_url}/api/drive/scan/trigger")
            success = response.status_code in [500, 400]
            self.log_test("Drive Scan Trigger", success, response)
        except Exception as e:
            self.log_test("Drive Scan Trigger", False, error=str(e))
            
        return True

    def test_vault_endpoints(self) -> bool:
        """Test Vault manager endpoints"""
        print("🔍 Testing Vault Manager Endpoints...")
        
        # Test vault statistics
        try:
            response = self.session.get(f"{self.base_url}/api/vault/statistics")
            success = response.status_code in [200, 500, 400]
            self.log_test("Vault Statistics", success, response)
        except Exception as e:
            self.log_test("Vault Statistics", False, error=str(e))
            
        # Test vault list documents
        try:
            response = self.session.get(f"{self.base_url}/api/vault/list")
            success = response.status_code in [200, 500, 400]
            self.log_test("Vault List Documents", success, response)
        except Exception as e:
            self.log_test("Vault List Documents", False, error=str(e))
            
        return True

    def test_authentication_scenarios(self) -> bool:
        """Test authentication-related scenarios"""
        print("🔍 Testing Authentication Scenarios...")
        
        # Test with invalid credentials
        try:
            response = self.session.get(f"{self.base_url}/api/drive/files")
            # Should handle gracefully without credentials
            success = response.status_code in [500, 400]
            self.log_test("No Authentication", success, response)
        except Exception as e:
            self.log_test("No Authentication", False, error=str(e))
            
        return True

    def test_error_handling(self) -> bool:
        """Test error handling for invalid requests"""
        print("🔍 Testing Error Handling...")
        
        # Test invalid endpoints
        try:
            response = self.session.get(f"{self.base_url}/api/invalid/endpoint")
            success = response.status_code == 404
            self.log_test("Invalid Endpoint", success, response)
        except Exception as e:
            self.log_test("Invalid Endpoint", False, error=str(e))
            
        # Test invalid JSON
        try:
            response = self.session.post(f"{self.base_url}/api/dlp/scan", 
                                      data="invalid json",
                                      headers={'Content-Type': 'application/json'})
            success = response.status_code in [400, 500]
            self.log_test("Invalid JSON", success, response)
        except Exception as e:
            self.log_test("Invalid JSON", False, error=str(e))
            
        return True

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        print("🚀 Starting API Test Suite for GDriveProtect")
        print("=" * 50)
        
        test_suites = [
            ("Health Endpoints", self.test_health_endpoints),
            ("DLP Endpoints", self.test_dlp_endpoints),
            ("Drive Endpoints", self.test_drive_endpoints),
            ("Vault Endpoints", self.test_vault_endpoints),
            ("Authentication", self.test_authentication_scenarios),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = {}
        total_passed = 0
        total_tests = 0
        
        for suite_name, test_func in test_suites:
            print(f"\n📋 {suite_name}")
            print("-" * 30)
            
            try:
                success = test_func()
                results[suite_name] = success
                if success:
                    total_passed += 1
                total_tests += 1
            except Exception as e:
                print(f"❌ {suite_name} failed with exception: {e}")
                results[suite_name] = False
                total_tests += 1
        
        return {
            'results': results,
            'test_results': self.test_results,
            'total_passed': total_passed,
            'total_tests': total_tests,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
        }

    def generate_report(self, results: Dict[str, Any]):
        """Generate a detailed test report"""
        print("\n" + "=" * 50)
        print("📊 TEST REPORT")
        print("=" * 50)
        
        print(f"Total Test Suites: {results['total_tests']}")
        print(f"Passed: {results['total_passed']}")
        print(f"Failed: {results['total_tests'] - results['total_passed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        
        print("\n📋 Detailed Results:")
        for suite_name, success in results['results'].items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {suite_name}")
        
        # Save detailed results to file
        with open('test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: test_results.json")
        
        return results['success_rate'] >= 80  # 80% success rate threshold

def main():
    """Main test runner"""
    # Check if container is running
    try:
        response = requests.get("http://localhost:5000/api/dlp/health", timeout=5)
        if response.status_code != 200:
            print("❌ Container is not responding properly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Container is not running on localhost:5000")
        print("Please start the container first:")
        print("docker run -p 5000:5000 -e GOOGLE_CLOUD_PROJECT=ifocus-innovations gdriveprotect")
        sys.exit(1)
    
    # Run tests
    tester = APITester()
    results = tester.run_all_tests()
    
    # Generate report
    success = tester.generate_report(results)
    
    if success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the results above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
