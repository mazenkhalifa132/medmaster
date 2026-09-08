from django.db import models


class TelegramGroup(models.Model):
    """Public Telegram group/channel used by one academic year."""

    YEAR_CHOICES = tuple((year, f'Year {year}') for year in range(1, 6))

    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, unique=True)
    handle = models.CharField(
        max_length=128,
        default='medmaster012',
        help_text='Public Telegram handle, without @ or the t.me/ prefix.',
    )

    class Meta:
        ordering = ('year',)
        verbose_name = 'Telegram group'
        verbose_name_plural = 'Telegram groups'

    def __str__(self):
        return f'Year {self.year}: @{self.handle}'

    @property
    def normalized_handle(self):
        return self.handle.strip().removeprefix('@').removeprefix('https://t.me/').removeprefix('http://t.me/').strip('/')

    @property
    def public_url(self):
        return f'https://t.me/{self.normalized_handle}'

    @property
    def preview_url(self):
        return f'https://t.me/s/{self.normalized_handle}'
