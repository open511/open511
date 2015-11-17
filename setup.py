try:
    import setuptools
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()

from setuptools import setup, find_packages


description = ''
import sys
if 'register' in sys.argv or 'upload' in sys.argv:
    try:
        import pypandoc
        description = pypandoc.convert('README.md', 'rst')
    except (IOError, ImportError):
        description = open('README.md').read()

setup(
    name = "open511",
    version = "0.5",
    url='https://github.com/open511/open511',
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        'lxml>=2.3',
        'pytz',
    ],
    entry_points = {
        'console_scripts': [
            'open511-validate = open511.validator.cmdline:validate_cmdline',
            'open511-convert = open511.converter.cmdline:convert_cmdline'
        ]
    },
    author = 'Michael Mulley',
    author_email = 'open511@opennorth.ca',
    license='MIT',
    classifiers = [
         'Development Status :: 4 - Beta',
         'Intended Audience :: Developers',
         'Programming Language :: Python :: 2.7',
         'Programming Language :: Python :: 3.5',
         'License :: OSI Approved :: MIT License',
    ],
    description = 'Tools supporting the Open511 format, which aims to make road information open and shareable.',
    long_description = description,
)
