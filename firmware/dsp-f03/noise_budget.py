"""重算候选滤波下20–450Hz噪声；沿用未实测线性模型。"""
import csv
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from scipy import signal
from generate import reference

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'front-end-ab'))
import simulate as model


def main():
    design = ROOT.parent / 'easyeda-sch/design.json'
    parts = {p['ref']: p for p in json.loads(design.read_text())['parts']}
    for channel in range(1, 9):
        for leg in 'PN':
            assert all(parts[f'R{channel}{leg}{suffix}']['value']=='1M' for suffix in 'ABCD')
            assert all(parts[f'R{channel}{leg}{suffix}']['value']=='10M' for suffix in 'EF')
    f = np.linspace(20, 450, 4301)
    rows = []
    for fs in (2000, 4000):
        for resistance in (100e3, 1e6):
            for capacitance in (25e-12, 100e-12, 200e-12):
                p = {**model.P, 'data_rate': fs, 'electrode_R': resistance, 'cable_C': capacitance}
                h, spectra, _ = model.leg(f, p)
                for notch in (False, True):
                    sos = reference(fs, notch).astype(np.float32).astype(float)
                    dsp = signal.sosfreqz(sos, worN=f, fs=fs)[1]
                    weight = abs(model.digital(f, p) * dsp)**2
                    components = {name: float(np.sqrt(np.trapezoid(2*v*weight, f))*1e6)
                                  for name, v in spectra.items()}
                    noise = float(np.sqrt(sum(value**2 for value in components.values())))
                    total_100 = abs(model.leg([100], p)[0][0] * model.digital(np.array([100]), p)[0] *
                                    signal.sosfreqz(sos, worN=[100], fs=fs)[1][0])
                    assert noise > 0 and total_100 > 0
                    rows.append(dict(fs_Hz=fs, notch=notch, Re_ohm=resistance, cable_pF=capacitance*1e12,
                                     network_noise_20_450_ADC_uVrms=noise,
                                     network_noise_100Hz_input_referred_uVrms=noise/total_100,
                                     gain100=float(total_100), **{k+'_uVrms': v for k, v in components.items()}))
    for i in range(0, len(rows), 2):
        assert rows[i+1]['network_noise_20_450_ADC_uVrms'] < rows[i]['network_noise_20_450_ADC_uVrms']
    with (ROOT / 'noise-budget.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    result = dict(status='模型预算，未实测', cases=len(rows), parameters=model.P,
                  band_Hz=[20, 450], rows=rows,
                  source_sha256={str(p.relative_to(ROOT.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (design, ROOT/'noise_budget.py', ROOT/'generate.py', ROOT.parent/'front-end-ab/simulate.py')},
                  excluded=['ADC自身噪声', '1/f与输入偏置/漏电噪声', 'RLD闭环',
                            '带外噪声折叠/抗混叠', '射频/电源与运动耦合', '真实线束和电极阻抗'])
    (ROOT / 'noise-budget.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    for row in rows:
        if row['Re_ohm']==100e3 and row['cable_pF']==100 and not row['notch']:
            print(json.dumps(row, ensure_ascii=False))


if __name__ == '__main__':
    main()
