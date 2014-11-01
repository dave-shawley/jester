import codecs
import setuptools
import sys

from jester import __version__


def read_requirements_file(name):
    try:
        with open(name) as req_file:
            return [line[0:line.index('#')] if '#' in line else line
                    for line in req_file]
    except IOError:
        pass


install_requirements = read_requirements_file('requirements.txt')
test_requirements = read_requirements_file('test-requirements.txt')
if sys.version_info < (2, 7):
    test_requirements.append('unittest2')
if sys.version_info < (3, ):
    test_requirements.append('mock>1.0,<2')


with codecs.open('README.rst', 'rb', encoding='utf-8') as file_obj:
    long_description = '\n' + file_obj.read()


setuptools.setup(
    name='jester',
    version=__version__,
    author='Dave Shawley',
    author_email='daveshawley@gmail.com',
    url='http://github.com/dave-shawley/jester',
    description='Asynchronous HTTP request handler',
    long_description=long_description,
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    zip_safe=True,
    platforms='any',
    install_requires=install_requirements,
    test_suite='nose.collector',
    tests_require=test_requirements,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Development Status :: 1 - Planning',
    ],
)
