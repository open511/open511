from setuptools import setup, find_packages

setup(
    name = "open511-validator",
    version = "0.1",
    url='https://github.com/opennorth/open511-validator',
    license = "",
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        'lxml>=2.3'
    ],
    entry_points = {
        'console_scripts': [
            'open511-validate = open511_validator.cmdline:validate_cmdline',
            'open511-convert = open511_validator.cmdline:convert_cmdline'
        ]
    },
)
