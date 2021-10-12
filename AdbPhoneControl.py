import subprocess
import re
import time

class AdbPhoneControl():
	def __init__(self, sn=None):
		self.connected = None
		self.connect(sn)

	def run_cmd(self, cmd, capture_output=True, shell=True, check=True, encoding='utf-8'):
		ret = subprocess.run(cmd, capture_output=capture_output, shell=shell, check=check, encoding=encoding)
		return ret.stdout.strip()

	def connect(self, sn=None, err=False):
		ret = self.adb_devices()
		cnt = len(ret)
		if cnt < 1:
			self.connected = None
			msg = 'No device connected!'
		elif sn:
			if sn not in ret:
				self.connected = None
				msg = 'The selected device is not connected!'
			elif 'unauthorized' == ret[sn]:
				self.connected = None
				msg = 'Selected device is production builds, please allow the USB debugging!'
			else:
				self.connected = sn
				msg = 'Successfully connect to the selected device.'
		else:
			sn = list(ret)[0]
			if 'unauthorized' == ret[sn]:
				self.connected = None
				msg = 'Connected device is production builds, please allow the USB debugging!'
			else:
				self.connected = sn
				if cnt > 1:
					msg = 'More than one devices connected, successfully connect to the first device.'
				else:
					msg = 'Successfully connect to the connected device.'
		if err:
			return msg

	def adb_devices(self):
		ret = self.run_cmd(['adb', 'devices'])
		devices = re.findall(r'^([a-zA-Z0-9]*)\s*?(device|unauthorized)$', ret, flags=re.M)
		return dict(devices)

	def adb_root(self):
		ret = self.run_cmd(['adb', 'root'])
		if 'adbd as root' not in ret:
			raise Exception('Run adb root fail!')

	def adb_shell_settings(self, args):
		cmd = ['adb', 'shell', 'settings']
		cmd.extend(args)
		return self.run_cmd(cmd)

	def adb_shell_dumpsys(self, activity, grep):
		cmd = ['adb', 'shell', 'dumpsys']
		cmd.extend([activity, '| grep', grep])
		return self.run_cmd(cmd)

	def adb_shell_input(self, args):
		cmd = ['adb', 'shell', 'input']
		cmd.extend(args)
		self.run_cmd(cmd)

	def get_system_volume(self, usecase, scenario):
		args = ['get', 'system', 'volume_'+usecase+'_'+scenario]
		try:
			return int(self.adb_shell_settings(args))
		except:
			print('Get system volume fail!')

	def key_volume(self, key):
		args = ['keyevent', 'KEYCODE_VOLUME_'+key]
		self.adb_shell_input(args)

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
				self.key_volume('DOWN')
			elif current < target:
				self.key_volume('UP')
			time.sleep(0.5)
			current = self.get_system_volume(usecase, scenario)
			if current == last:
				cnt += 1
			else:
				last = current
			if cnt >= 3:
				raise Exception('Fail to set the target volume!')

	def get_call_state(self, sim=0):
		ret = self.adb_shell_dumpsys('telephony.registry', 'mCallState')
		states = re.findall(r'mCallState=(\d)', ret, flags=re.M)
		# 0:idle, 1:ringing, 2:incall
		if sim > len(states) or sim < 0:
			raise Exception('The specified SIM card do not exist!')
		elif sim > 0:
			return states[sim-1]
		else:
			return states

	def checkVolChange(self, usecase, scenario):
		flag = False
		last = current = self.get_system_volume(usecase, scenario)
		self.key_volume('UP')
		time.sleep(0.5)
		self.key_volume('UP')
		time.sleep(0.5)
		current = self.get_system_volume(usecase, scenario)
		if current > last:
			flag = True
		last = current = self.get_system_volume(usecase, scenario)
		self.key_volume('DOWN')
		time.sleep(0.5)
		self.key_volume('DOWN')
		time.sleep(0.5)
		current = self.get_system_volume(usecase, scenario)
		if current < last:
			flag = True
		return flag

	def getMINVol(self, usecase, scenario):
		cnt = 0
		last = current = self.get_system_volume(usecase, scenario)
		while cnt < 3:
			self.key_volume('DOWN')
			time.sleep(0.5)
			current = self.get_system_volume(usecase, scenario)
			if current < last:
				last = current
			else:
				cnt += 1
		return current

	def getMAXVol(self, usecase, scenario):
		cnt = 0
		last = current = self.get_system_volume(usecase, scenario)
		while cnt < 3:
			self.key_volume('UP')
			time.sleep(0.5)
			current = self.get_system_volume(usecase, scenario)
			if current > last:
				last = current
			else:
				cnt += 1
		return current
