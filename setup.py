from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='my-python-app',
    version='1.0.0',
    author='Your Name',
    author_email='your_email@example.com',
    description='A Python application',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/your_username/my-python-app',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        # Add your dependencies here
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)