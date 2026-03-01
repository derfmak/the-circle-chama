#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

python manage.py shell << EOF
from apps.members.models import ContributionType

defaults = [
    {
        'name': 'Monthly Contribution',
        'contribution_type': 'monthly',
        'amount': 1000.00,
        'description': 'Monthly contribution of KES 1,000 due by 10th of each month. Late payment attracts KES 200 fine.',
        'deadline_day': 10,
        'is_active': True
    },
    {
        'name': 'Quarterly Contribution',
        'contribution_type': 'quarterly',
        'amount': 7000.00,
        'description': 'Quarterly contribution of KES 7,000 due by end of April, August, and December.',
        'deadline_day': None,
        'is_active': True
    },
    {
        'name': 'Registration Fee',
        'contribution_type': 'registration',
        'amount': 1000.00,
        'description': 'One-time registration fee for new members.',
        'deadline_day': None,
        'is_active': True
    }
]

for default in defaults:
    ContributionType.objects.get_or_create(
        contribution_type=default['contribution_type'],
        defaults=default
    )

print('Default contribution types created successfully.')
EOF