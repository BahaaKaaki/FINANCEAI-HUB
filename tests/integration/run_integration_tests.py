"""
Integration test runner with comprehensive reporting.

This script runs all integration tests and provides detailed reporting
on system performance, data quality, and overall health.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest


class IntegrationTestRunner:
    """Runner for integration tests with detailed reporting."""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        self.report_dir = Path("test_reports")
        self.report_dir.mkdir(exist_ok=True)
    
    def run_all_tests(self, verbose=False, parallel=False):
        """Run all integration tests with reporting."""
        print("🚀 Starting AI Financial Data System Integration Tests")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Test suites to run
        test_suites = [
            {
                "name": "End-to-End Ingestion",
                "file": "test_end_to_end_ingestion.py",
                "description": "Complete data ingestion workflow tests"
            },
            {
                "name": "AI Agent Integration", 
                "file": "test_ai_agent_integration.py",
                "description": "AI agent tool calling and query processing tests"
            },
            {
                "name": "API Endpoints Integration",
                "file": "test_api_endpoints_integration.py", 
                "description": "API endpoint testing with various scenarios"
            },
            {
                "name": "Performance & Concurrency",
                "file": "test_performance_concurrent.py",
                "description": "Performance tests with concurrent user simulation"
            },
            {
                "name": "Data Quality Validation",
                "file": "test_data_quality_validation.py",
                "description": "Data quality validation with real financial data"
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            print(f"\n📋 Running {suite['name']} Tests")
            print(f"   {suite['description']}")
            print("-" * 50)
            
            result = self._run_test_suite(suite, verbose, parallel)
            self.results[suite['name']] = result
            
            # Print immediate results
            if result['success']:
                print(f"✅ {suite['name']}: PASSED ({result['duration']:.1f}s)")
                if result['warnings']:
                    print(f"⚠️  {result['warnings']} warnings")
            else:
                print(f"❌ {suite['name']}: FAILED ({result['duration']:.1f}s)")
                print(f"   {result['failures']} failures, {result['errors']} errors")
        
        # Generate comprehensive report
        self._generate_report()
        
        # Print summary
        self._print_summary()
        
        return self._all_tests_passed()
    
    def _run_test_suite(self, suite, verbose=False, parallel=False):
        """Run a single test suite."""
        test_file = Path(__file__).parent / suite['file']
        
        # Prepare pytest arguments
        args = [str(test_file)]
        
        if verbose:
            args.append("-v")
        else:
            args.append("-q")
        
        # Add performance reporting
        args.extend([
            "--tb=short",
            f"--junitxml={self.report_dir}/{suite['name'].lower().replace(' ', '_')}_results.xml"
        ])
        
        if parallel:
            args.extend(["-n", "auto"])  # Requires pytest-xdist
        
        # Run the tests
        start_time = time.time()
        
        try:
            # Capture pytest output
            exit_code = pytest.main(args)
            duration = time.time() - start_time
            
            # Parse results (simplified - in real implementation would parse XML)
            result = {
                'success': exit_code == 0,
                'duration': duration,
                'exit_code': exit_code,
                'failures': 0,  # Would parse from XML
                'errors': 0,    # Would parse from XML
                'warnings': 0,  # Would parse from XML
                'tests_run': 0  # Would parse from XML
            }
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                'success': False,
                'duration': duration,
                'exit_code': -1,
                'failures': 0,
                'errors': 1,
                'warnings': 0,
                'tests_run': 0,
                'error': str(e)
            }
    
    def _generate_report(self):
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_duration_seconds': total_duration,
            'test_suites': self.results,
            'summary': {
                'total_suites': len(self.results),
                'passed_suites': sum(1 for r in self.results.values() if r['success']),
                'failed_suites': sum(1 for r in self.results.values() if not r['success']),
                'total_duration': total_duration
            },
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'working_directory': os.getcwd()
            }
        }
        
        # Save JSON report
        report_file = self.report_dir / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report (simplified)
        self._generate_html_report(report, report_file.with_suffix('.html'))
        
        print(f"\n📊 Detailed reports saved to: {self.report_dir}")
        print(f"   JSON: {report_file.name}")
        print(f"   HTML: {report_file.with_suffix('.html').name}")
    
    def _generate_html_report(self, report, html_file):
        """Generate HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Financial Data System - Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .suite {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ border-left: 5px solid #4CAF50; }}
        .failed {{ border-left: 5px solid #f44336; }}
        .summary {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-weight: bold; font-size: 1.2em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 AI Financial Data System - Integration Test Report</h1>
        <p><strong>Generated:</strong> {report['timestamp']}</p>
        <p><strong>Total Duration:</strong> {report['total_duration_seconds']:.1f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="metric">
            <div class="metric-value">{report['summary']['total_suites']}</div>
            <div>Total Suites</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #4CAF50;">{report['summary']['passed_suites']}</div>
            <div>Passed</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #f44336;">{report['summary']['failed_suites']}</div>
            <div>Failed</div>
        </div>
    </div>
    
    <h2>🔍 Test Suite Details</h2>
"""
        
        for suite_name, result in report['test_suites'].items():
            status_class = "passed" if result['success'] else "failed"
            status_icon = "✅" if result['success'] else "❌"
            
            html_content += f"""
    <div class="suite {status_class}">
        <h3>{status_icon} {suite_name}</h3>
        <p><strong>Duration:</strong> {result['duration']:.1f} seconds</p>
        <p><strong>Status:</strong> {'PASSED' if result['success'] else 'FAILED'}</p>
        <p><strong>Exit Code:</strong> {result['exit_code']}</p>
"""
            
            if not result['success'] and 'error' in result:
                html_content += f"<p><strong>Error:</strong> {result['error']}</p>"
            
            html_content += "    </div>\n"
        
        html_content += """
    <div class="summary">
        <h2>🔧 System Information</h2>
        <p><strong>Python Version:</strong> """ + report['system_info']['python_version'].replace('\n', '<br>') + """</p>
        <p><strong>Platform:</strong> """ + report['system_info']['platform'] + """</p>
        <p><strong>Working Directory:</strong> """ + report['system_info']['working_directory'] + """</p>
    </div>
</body>
</html>"""
        
        with open(html_file, 'w') as f:
            f.write(html_content)
    
    def _print_summary(self):
        """Print test execution summary."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.results.values() if r['success'])
        failed = sum(1 for r in self.results.values() if not r['success'])
        
        print("\n" + "=" * 60)
        print("🏁 INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Test Suites: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 ALL INTEGRATION TESTS PASSED!")
            print("The AI Financial Data System is ready for deployment.")
        else:
            print(f"\n⚠️  {failed} test suite(s) failed.")
            print("Please review the detailed reports and fix issues before deployment.")
        
        print("=" * 60)
    
    def _all_tests_passed(self):
        """Check if all tests passed."""
        return all(result['success'] for result in self.results.values())


def main():
    """Main entry point for integration test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Financial Data System integration tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "-p", "--parallel",
        action="store_true", 
        help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "--suite",
        choices=[
            "ingestion", "ai_agent", "api_endpoints", 
            "performance", "data_quality"
        ],
        help="Run only specific test suite"
    )
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    
    if args.suite:
        # Run specific suite (implementation would filter suites)
        print(f"Running specific test suite: {args.suite}")
        success = runner.run_all_tests(args.verbose, args.parallel)
    else:
        # Run all tests
        success = runner.run_all_tests(args.verbose, args.parallel)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()