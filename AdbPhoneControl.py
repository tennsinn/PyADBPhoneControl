import subprocess
import re
import time

class AdbPhoneControl():
	def __init__(self, id=None):
		self.adb_devices(id)

	def run_cmd(self, cmd, capture_output=True, shell=True, check=True, encoding='utf-8'):
		ret = subprocess.run(cmd, capture_output=capture_output, shell=shell, check=check, encoding=encoding)
		return ret.stdout.strip()

	def adb_devices(self, id=None):
		ret = self.run_cmd(['adb', 'devices'])
		devices = re.findall(r'^([a-zA-Z0-9]*)\s*?device$', ret, flags=re.M)
		cnt = len(devices)
		if cnt < 1:
			raise Exception('No device connected!')
		elif cnt > 1:
			raise Exception('More than one devices connected!')
		elif 'unauthorized' in ret:
			raise Exception('Connected device is production builds, please allow the USB debugging!')
		elif not id:
			self.id = devices[0]
		elif id not in devices:
			raise Exception('The required device is not connected!')
		else:
			self.id = id

	def adb_root(self):
		ret = self.run_cmd(['adb', 'root'])
		if 'adbd as root' not in ret:
			raise Exception('Run adb root fail!')

	def adb_shell_settings(self, args):
		cmd = ['adb', 'shell', 'settings']
		cmd.extend(args)
		return self.run_cmd(cmd)

	def get_system_volume(self, usecase, scenario):
		args = ['get', 'system', 'volume_'+usecase+'_'+scenario]
		try:
			return int(self.adb_shell_settings(args))
		except:
			print('Get system volume fail!')

	def key_volume(self, key):
		args = ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_VOLUME_'+key]
		self.run_cmd(args)

	def set_vol_by_key(self, target, usecase, scenario):
		usecases = ['music', 'voice']
		if usecase not in usecases:
			raise Exception('The usecase is not supported!')
		scenarios = ['earpiece', 'headset', 'speaker']
		if scenario not in scenarios:
			raise Exception('The scenario is not supported!')
		cnt = 0
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

if __name__ == '__main__':
	adb = AdbPhoneControl()
