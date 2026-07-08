# -*- coding: utf-8 -*-
import os
import time

def write_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(str(content))
        return True
    except Exception:
        return False

def pwm_export(chip_path, channel=0):
    write_file(os.path.join(chip_path, 'export'), channel)
    time.sleep(0.05)
    pwm0 = os.path.join(chip_path, f'pwm{channel}')
    return os.path.isdir(pwm0)

def pwm_set_period(chip_path, period_ns, channel=0):
    pwm0 = os.path.join(chip_path, f'pwm{channel}')
    return write_file(os.path.join(pwm0, 'period'), period_ns)

def pwm_set_duty(chip_path, duty_ns, channel=0):
    pwm0 = os.path.join(chip_path, f'pwm{channel}')
    if not write_file(os.path.join(pwm0, 'duty_cycle'), duty_ns):
        return False
    return write_file(os.path.join(pwm0, 'enable'), 1)

def pwm_disable(chip_path, channel=0):
    pwm0 = os.path.join(chip_path, f'pwm{channel}')
    write_file(os.path.join(pwm0, 'enable'), 0)

def pwm_unexport(chip_path, channel=0):
    write_file(os.path.join(chip_path, 'unexport'), channel)

def pwm_init(chip_path, period_ns=5000000, channel=0):
    if not pwm_export(chip_path, channel):
        return False
    if not pwm_set_period(chip_path, period_ns, channel):
        return False
    pwm_set_duty(chip_path, 500000, channel)
    return True

# 新增：直接写入占空比（不使能），用于测试脚本和精确控制
def pwm_write(chip_path, duty_ns, channel=0):
    pwm0 = os.path.join(chip_path, f'pwm{channel}')
    return write_file(os.path.join(pwm0, 'duty_cycle'), duty_ns)
