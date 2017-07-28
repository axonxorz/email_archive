from setuptools import setup
import versioneer


setup(
    name='email_archive',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author='bzerr',
    author_email='bzerr@brainwire.ca',
    license='MIT',
    url='https://github.com/axonxorz/email_archive',
    install_requires=open('requirements.txt').readlines(),
    extras_require=dict(dev=open('requirements-dev.txt').readlines()),
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
            'email-archive-message=email_archive.archive:main',
            'email-index-daemon=email_archive.index_daemon:main'
        ]
    ),
)

