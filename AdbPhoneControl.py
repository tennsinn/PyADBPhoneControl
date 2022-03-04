import subprocess
import re
import time

class AdbCallState():
	IDLE = '0'
	RING = '1'
	INCALL = '2'

class AdbPhoneControl():
	def __init__(self, sn=None):
		self.connected = None

	@staticmethod
	def cmd(cmd, capture_output=True, shell=True, check=True, encoding='utf-8'):
		ret = subprocess.run(cmd, capture_output=capture_output, shell=shell, check=check, encoding=encoding)
		return ret.stdout.strip()

	def connect(self, sn=None, err=False):
		ret = self.devices()
		cnt = len(ret)
		if cnt < 1:
			self.connected = None
			err = True
			msg = 'No device connected!'
		elif sn:
			if sn not in ret:
				self.connected = None
				err = True
				msg = 'The selected device is not connected!'
			elif 'unauthorized' == ret[sn]:
				self.connected = None
				err = True
				msg = 'Selected device is production builds, please allow the USB debugging!'
			else:
				self.connected = sn
				err = False
				msg = 'Successfully connect to the selected device.'
		else:
			sn = list(ret)[0]
			if 'unauthorized' == ret[sn]:
				self.connected = None
				err = True
				msg = 'Connected device is production builds, please allow the USB debugging!'
			else:
				self.connected = sn
				err = False
				if cnt > 1:
					msg = 'More than one devices connected, successfully connect to the first device.'
				else:
					msg = 'Successfully connect to the connected device.'
		if err:
			raise Exception(msg)
		return msg

	@staticmethod
	def devices():
		ret = AdbPhoneControl.cmd(['adb', 'devices'])
		devices = re.findall(r'^([a-zA-Z0-9]*)\s*?(device|unauthorized)$', ret, flags=re.M)
		return dict(devices)

	@staticmethod
	def root():
		ret = AdbPhoneControl.cmd(['adb', 'root'])
		if 'adbd as root' not in ret:
			raise Exception('Run adb root fail!')

	@staticmethod
	def settings(args):
		cmd = ['adb', 'shell', 'settings']
		cmd.extend(args)
		return AdbPhoneControl.cmd(cmd)

	@staticmethod
	def dumpsys(activity, grep=None):
		cmd = ['adb', 'shell', 'dumpsys', activity]
		if grep:
			cmd.extend(['| grep', grep])
		return AdbPhoneControl.cmd(cmd)

	@staticmethod
	def input(args):
		cmd = ['adb', 'shell', 'input']
		cmd.extend(args)
		AdbPhoneControl.cmd(cmd)

	def get_system_volume(self, usecase, scenario):
		args = ['get', 'system', 'volume_'+usecase+'_'+scenario]
		try:
			return int(self.settings(args))
		except:
			print('Get system volume fail!')

	@staticmethod
	def key(keycode):
		if keycode.isdigit():
			args = ['keyevent', keycode]
		else:
			args = ['keyevent', 'KEYCODE_'+keycode]
		AdbPhoneControl.input(args)

	@staticmethod
	def key_volume_up():
		args = ['keyevent', 'KEYCODE_VOLUME_UP']
		AdbPhoneControl.input(args)

	@staticmethod
	def key_volume_down():
		args = ['keyevent', 'KEYCODE_VOLUME_DOWN']
		AdbPhoneControl.input(args)

	@staticmethod
	def key_call():
		args = ['keyevent', 'KEYCODE_CALL']
		AdbPhoneControl.input(args)

	@staticmethod
	def key_endcall():
		args = ['keyevent', 'KEYCODE_ENDCALL']
		AdbPhoneControl.input(args)

	def get_target_vol(self, volume, MINVol, MAXVol, NOMVol=None):
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

	def set_vol_by_key(self, usecase, scenario, volume, MINVol, MAXVol, NOMVol):
		usecases = ['music', 'voice']
		if usecase not in usecases:
			raise Exception('The usecase is not supported!')
		scenarios = ['earpiece', 'headset', 'speaker']
		if scenario not in scenarios:
			raise Exception('The scenario is not supported!')
		cnt = 0
		target = self.get_target_vol(volume, MINVol, MAXVol, NOMVol)
		last = current = self.get_system_volume(usecase, scenario)
		while current != target and cnt < 3:
			if current > target:
				self.key_volume_down()
			elif current < target:
				self.key_volume_up()
			time.sleep(0.5)
			current = self.get_system_volume(usecase, scenario)
			if current == last:
				cnt += 1
			else:
				last = current
			if cnt >= 3:
				raise Exception('Fail to set the target volume!')

	@staticmethod
	def call_state(sim=0):
		ret = AdbPhoneControl.dumpsys('telephony.registry', 'mCallState')
		states = re.findall(r'mCallState=(\d)', ret, flags=re.M)
		if sim > len(states) or sim < 0:
			raise Exception('The specified SIM card do not exist!')
		elif sim > 0:
			return states[sim-1]
		else:
			return states

	def check_vol_change(self, usecase, scenario):
		flag = False
		last = current = self.get_system_volume(usecase, scenario)
		self.key_volume_up()
		time.sleep(0.5)
		self.key_volume_up()
		time.sleep(0.5)
		current = self.get_system_volume(usecase, scenario)
		if current > last:
			flag = True
		last = current = self.get_system_volume(usecase, scenario)
		self.key_volume_down()
		time.sleep(0.5)
		self.key_volume_down()
		time.sleep(0.5)
		current = self.get_system_volume(usecase, scenario)
		if current < last:
			flag = True
		return flag

	def stream_volumes(self, stream):
		ret = self.dumpsys('audio')
		states = re.search(r'- STREAM_'+stream+r':\n *Muted: *(?P<Muted>true|false)\n *Muted Internally: *(?P<MutedInternally>true|false)\n *Min: *(?P<Min>\d+)\n *Max: *(?P<Max>\d+)\n *streamVolume: *(?P<streamVolume>\d+)\n *Current: *(?P<Current>.*?)\n *Devices: *(?P<Devices>.*?)\n', ret, re.S)
		if not states:
			raise Exception('Do not find the related stream volumes.')
		return states.groupdict()
