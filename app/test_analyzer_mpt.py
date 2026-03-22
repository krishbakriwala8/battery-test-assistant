from analyzer import BatteryTestAnalyzer

analyzer = BatteryTestAnalyzer(
    csv_path='../data/sample_logs/SINTEF__NaCR32140-MP10-04__2025-08-25__CCCV_0p02C_25degC__BioLogic__Outlier_Bug.mpt',
    config_path='../data/sample_configs/thresholds_naion.json'
)
result = analyzer.run()

if "error" in result:
    print("❌ Error:", result["error"])
else:
    print(f"Test Result: {'✅ PASS' if result['pass'] else '❌ FAIL'}")
    print("\n📊 Statistics:")
    for signal, stats in result['statistics'].items():
        print(f"  {signal}: min={stats['min']:.3f}, max={stats['max']:.3f}")
    
    print("\n📋 Violations:")
    if result['violations']:
        for v in result['violations']:
            print(f"  • {v['signal']} at t={v['timestamp']:.2f}: {v['value']:.3f} ({v['rule']})")
    else:
        print("  No violations found (thresholds may be too loose)")