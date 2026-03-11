from setuptools import setup, find_packages
setup(
    name='pwdx-ctl',
    version='0.1.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['click','requests'],
    entry_points={'console_scripts': ['pwdx-ctl=pwdx_ctl.cli:cli']},
)
