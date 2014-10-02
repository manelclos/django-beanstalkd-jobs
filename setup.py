from setuptools import setup, find_packages


setup(
    name='django-beanstalkd-jobs',
    version='0.3',
    description='A jobs system using beanstalkd, clients and workers '
                'as simple functions in a Django project',
    long_description=open('README.md').read(),
    author='Manel Clos',
    author_email='manelclos@gmail.com',
    url='http://github.com/manelclos/django-beanstalkd-jobs',
    license='MPL',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['pyyaml', 'beanstalkc'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
