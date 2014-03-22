import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = "open511",
    version = "0.2",
    url='https://github.com/opennorth/open511',
    license = "",
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        'lxml>=2.3'
    ],
    entry_points = {
        'console_scripts': [
            'open511-validate = open511.validator.cmdline:validate_cmdline',
            'open511-convert = open511.converter.cmdline:convert_cmdline'
        ]
    },
    namespace_packages = ['open511'],
)
