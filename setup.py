import re
from setuptools import setup
import subprocess


def get_version():
	from email_archive import __version__
	git_rev = get_git_rev()
	if git_rev:
		return '{}+git-{}'.format(__version__, git_rev)
	return __version__


def get_git_rev():
	try:
		return subprocess.check_output('git describe --always --dirty --tags', shell=True)
	except subprocess.CalledProcessError:
		return None


setup(
    name='email_archive',
    version=get_version(),
    author='bzerr',
    author_email='bzerr@brainwire.ca',
    license='MIT',
    url='https://github.com/axonxorz/email_archive',

    install_requires=open('requirements.txt').readlines(),
    extras_require=dict(),
    description='Email retention archiver and indexer for postfix',
    long_description=open('README.rst', 'r').read(),
    keywords=['python'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    packages=["email_archive"],
    data_files=[],
    entry_points=dict(
        console_scripts=[
            'email_archive=email_archive.cli:cli'
        ]
    ),
)

