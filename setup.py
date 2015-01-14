from distutils.core import setup
import sys

with open('README') as fh:
    long_desc = fh.read()

if sys.version_info < (3, 4):
    requirements = ['scription', 'enum34']
else:
    requirements = ['scription']

setup( name='xaml',
       version= '0.1.01',
       license='BSD License',
       description='XML Abstract Markup Language',
       long_description=long_desc,
       py_modules=['xaml', 'xaml_test'],
       provides=['xaml'],
       install_requires=requirements,
       author='Ethan Furman',
       author_email='ethan@stoneleaf.us',
       url='https://bitbucket.org/stoneleaf.xaml',
       classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.3',
            'Topic :: Software Development',
            'Topic :: Text Processing :: Markup :: HTML',
            'Topic :: Text Processing :: Markup :: XML',
            ],
    )

