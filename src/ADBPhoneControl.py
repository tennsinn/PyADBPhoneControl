__version__ = '0.9.5'

import subprocess
import re
import time

class CallState():
    IDLE = '0'
    RING = '1'
    INCALL = '2'

def run(cmd, capture_output=True, shell=True, check=True, encoding='utf-8'):
    try:
        ret = subprocess.run(cmd, capture_output=capture_output, shell=shell, check=check, encoding=encoding)
    except subprocess.CalledProcessError:
        subprocess.run(['adb', 'kill-server'], capture_output=capture_output, shell=shell, check=check, encoding=encoding)
        time.sleep(5)
        ret = subprocess.run(cmd, capture_output=capture_output, shell=shell, check=check, encoding=encoding)
    return ret.stdout.strip()

def connected(sn=None, m=False):
    ret = devices()
    cnt = len(ret)
    if cnt < 1:
        connected = False
        err = True
        msg = 'No device connected!'
    elif sn:
        if sn not in ret:
            connected = False
            err = True
            msg = 'The selected device is not connected!'
        elif 'unauthorized' == ret[sn]:
            connected = False
            err = True
            msg = 'Selected device is production builds, please allow the USB debugging!'
        else:
            connected = True
            err = False
            msg = 'Successfully connect to the selected device.'
    else:
        sn = list(ret)[0]
        if 'unauthorized' == ret[sn]:
            connected = False
            err = True
            msg = 'Connected device is production builds, please allow the USB debugging!'
        else:
            connected = True
            err = False
            if cnt > 1:
                msg = 'More than one devices connected, successfully connect to the first device.'
            else:
                msg = 'Successfully connect to the connected device.'
    if m and err:
        raise Exception(msg)
    elif m:
        print(msg)
    return connected

def kill():
    cmd = ['adb', 'kill-server']
    return run(cmd)

def connect(addr):
    cmd = ['adb', 'connect', addr]
    return run(cmd)

def devices():
    ret = run(['adb', 'devices'])
    devices = re.findall(r'^([a-zA-Z0-9.:]*)\s*?(device|unauthorized)$', ret, flags=re.M)
    return dict(devices)

def root():
    ret = run(['adb', 'root'])
    if 'adbd as root' not in ret:
        raise Exception('Run adb root fail!')

def settings(args):
    cmd = ['adb', 'shell', 'settings']
    cmd.extend(args)
    return run(cmd)

def dumpsys(activity, grep=None):
    cmd = ['adb', 'shell', 'dumpsys', activity]
    if grep:
        cmd.extend(['| grep', grep])
    return run(cmd)

def input(args):
    cmd = ['adb', 'shell', 'input']
    cmd.extend(args)
    run(cmd)

def get_system_volume(usecase, scenario):
    args = ['get', 'system', 'volume_'+usecase+'_'+scenario]
    vol = settings(args)
    if 'null' == vol:
        key_volume_up()
        key_volume_down()
        vol = settings(args)
    if vol.isdigit():
        return int(vol)
    else:
        raise Exception('Fail to get the required system volume!')

def key(keycode):
    if keycode.isdigit():
        args = ['keyevent', keycode]
    else:
        args = ['keyevent', 'KEYCODE_'+keycode]
    input(args)

def key_volume_up():
    args = ['keyevent', 'KEYCODE_VOLUME_UP']
    input(args)
    time.sleep(0.5)

def key_volume_down():
    args = ['keyevent', 'KEYCODE_VOLUME_DOWN']
    input(args)
    time.sleep(0.5)

def key_call():
    args = ['keyevent', 'KEYCODE_CALL']
    input(args)

def key_endcall():
    args = ['keyevent', 'KEYCODE_ENDCALL']
    input(args)

def get_target_vol(volume, MINVol, MAXVol, NOMVol=None):
    if volume and (type(volume) == int or (type(volume) == str and volume.isdigit())):
        target = int(volume)
    elif volume and type(volume) == str and re.fullmatch(r'^(MAX|NOM|MIN)?(\+|\-)?\d*$', volume, re.I):
        if NOMVol == None and 'NOM' in volume.upper():
            raise Exception('Missing value of NOM volume!')
        volume = re.sub(r'(MAX|NOM|MIN)', r'\1Vol', volume.upper(), 0)
        target = eval(volume)
    else :
        raise Exception('Invalid volume value!')
    return max(min(target, MAXVol), MINVol)

def set_vol_by_key(usecase, scenario, volume, MINVol, MAXVol, NOMVol):
    cnt = 0
    target = get_target_vol(volume, MINVol, MAXVol, NOMVol)
    last = current = get_system_volume(usecase, scenario)
    while current != target and cnt <= 3:
        if current > target:
            key_volume_down()
        else:
            key_volume_up()
        current = get_system_volume(usecase, scenario)
        if current == last:
            cnt += 1
        else:
            last = current
    if cnt > 3:
        raise Exception('Fail to set the target volume!')

def call_state(sim=0):
    ret = dumpsys('telephony.registry', 'mCallState')
    states = re.findall(r'mCallState=(\d)', ret, flags=re.M)
    if sim > len(states) or sim < 0:
        raise Exception('The specified SIM card do not exist!')
    elif sim > 0:
        return states[sim-1]
    else:
        return states

def check_vol_change(usecase, scenario):
    flag = False
    last = current = get_system_volume(usecase, scenario)
    key_volume_up()
    current = get_system_volume(usecase, scenario)
    if current > last:
        flag = True
    else:
        last = current = get_system_volume(usecase, scenario)
        key_volume_down()
        current = get_system_volume(usecase, scenario)
        if current < last:
            flag = True
    return flag

def stream_volumes(stream):
    ret = dumpsys('audio')
    states = re.search(r'- STREAM_'+stream+r':(\n* *[^-]*?\n* *)?Min: *(?P<Min>\d+)(\n* *[^-]*?\n* *)?Max: *(?P<Max>\d+)(\n* *[^-]*?\n* *)?streamVolume: *(?P<streamVolume>\d+)(\n* *[^-]*?\n* *)?Current: *(?P<Current>(?: ?\d+ \(.*?\): \d+,?)+)(\n* *[^-]*?\n* *)?Devices: *(?P<Devices>.*?)(?:\(.*?\))?\n', ret, re.S)
    if not states:
        raise Exception('Do not find the related stream volumes.')
    return states.groupdict()
