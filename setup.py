from setuptools import setup
from src.ADBPhoneControl import __version__

setup(
    name='ADBPhoneControl',
    version=__version__,
    description='A simple library for controlling Android phones based on the ADB tool.',
    keywords=['adb', 'android'],
    author='tennsinn',
    author_email='rampage@tennsinn.com',
    url='https://github.com/tennsinn/PyADBPhoneControl',
    license='GNU General Public License v3.0',
    package_dir={'': 'src'},
    py_modules=['ADBPhoneControl'],
)
