from distutils.core import setup

with open('README') as fh:
    long_desc = fh.read()

setup( name='xaml',
       version= '0.1.00',
       license='BSD License',
       description='write XML without writing XML',
       long_description=long_desc,
       py_modules=['xaml', 'xaml_test'],
       provides=['xaml'],
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

