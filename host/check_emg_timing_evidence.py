"""Timing metadata must not turn host events into measured ADC/screen alignment."""
import usb_emg as u

def check():
    host = dict(recording_ack_host_ns=1_000_000_000)
    for device in ({}, dict(device_t0_ms=0, device_arm_us=0)):
        result = u.align_capture({**host, **device}, cue={'shown_ms': 1012},
                                 previews=[(100, 0), (110, 110_000_000)])
        assert result['device_clock_available'] == bool(device)
        assert result['sample_alignment_verified'] is False
        assert result['cue_sample_index_is_estimate'] is True
        assert result['cue_sample_index_estimate'] == result['cue_sample_index'] == 12
        assert result['cue_time_reference'] == 'browser_dom_update_wall_clock'
        log = u.timing_for_log(result)
        assert log['preview_max_host_gap_ms'] == 110
        assert log['preview_max_device_step_ms'] == 10
        assert 'cue_sample_index' not in log
    missing = u.align_capture(host)
    assert 'cue_sample_index_estimate' not in missing
    assert not missing['sample_alignment_verified']
    early = u.align_capture(host, cue={'shown_ms': 990})
    assert early['cue_sample_index_estimate'] == -10
    print('PASS: unknown timing stays unknown; host stall differs from device gap; compatibility retained')

if __name__ == '__main__':
    check()
