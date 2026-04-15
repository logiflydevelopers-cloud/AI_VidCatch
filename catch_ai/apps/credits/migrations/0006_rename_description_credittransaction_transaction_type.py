from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('credits', '0005_credittransaction_balance_before_usercredits_balance'),
    ]

    operations = [

        # STEP 2: reuse name
        migrations.RenameField(
            model_name='credittransaction',
            old_name='description',
            new_name='transaction_type',
        ),
    ]