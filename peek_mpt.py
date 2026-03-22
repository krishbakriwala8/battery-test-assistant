
with open('SINTEF__NaCR32140-MP10-04__2025-08-25__CCCV_0p02C_25degC__BioLogic__Outlier_Bug.mpt', 'r', encoding='latin1') as f:
    for i, line in enumerate(f):
        print(f"{i}: {line.strip()}")
        if i > 50:  
            break