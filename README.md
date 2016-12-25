# prototype1
For django prototype

FAQ

1. I get a ImportError: cannot import name patterns when I try to run manage.py

pip install django-guardian -U
This is because the dependency package version for guardian in userena is wrong. Upgrade to latest version will solve this issue.


2. When I sign up, I get a permission group does not exist exception.

Run python manage.py check_permission.
see FAQ 5.5.1 https://media.readthedocs.org/pdf/django-userena/latest/django-userena.pdf

3. Remember to run manage.py migrate whenever new models are introduced.