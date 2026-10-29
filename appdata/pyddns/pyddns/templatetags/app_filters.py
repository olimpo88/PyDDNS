from django import template
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe
from common import twofactor
from pyddns.models import SubDomain
from common.models import Activity_log
from django.conf import settings


register = template.Library()


@register.filter(name='count_domain')
def count_domain(user):
    count = SubDomain.objects.filter(user=user).count()
    return count


@register.filter(name='has_2fa')
def has_2fa(user):
    return twofactor.has_2fa(user)


@register.filter(name='last_ip')
def last_ip(subdomain):
    domain = '%s.%s' % (subdomain, settings.DNS_DOMAIN)
    try:
        last_activity = Activity_log.objects.filter(action="SYNC", code="good", domain=domain).latest('date')
        return last_activity.ip
    except Activity_log.DoesNotExist:
        return "---"


@register.filter(name='last_update')
def last_update(subdomain):
    domain = '%s.%s' % (subdomain, settings.DNS_DOMAIN)
    try:
        last_activity = Activity_log.objects.filter(action="SYNC", code="good", domain=domain).latest('date')
        return last_activity.date
    except Activity_log.DoesNotExist:
        return "---"


@register.filter(name='sparkline_24h')
def sparkline_24h(subdomain):
    """Render a 24-bucket SVG sparkline (one column per hour over the last
    24h). Each column is filled if a successful SYNC happened in that bucket,
    otherwise it shows as a thin grey gap."""
    domain = '%s.%s' % (subdomain, settings.DNS_DOMAIN)
    now = timezone.now()
    start = now - timedelta(hours=24)
    rows = list(
        Activity_log.objects
        .filter(action='SYNC', code='good', domain=domain, date__gte=start)
        .values_list('date', flat=True)
    )
    buckets = [False] * 24
    for d in rows:
        idx = int((d - start).total_seconds() // 3600)
        if 0 <= idx < 24:
            buckets[idx] = True

    width, height, gap = 90, 26, 1.6
    n = len(buckets)
    bw = (width - gap * (n - 1)) / n
    parts = [f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">']
    for i, ok in enumerate(buckets):
        x = i * (bw + gap)
        y = 4 if ok else 10
        h = (height - 8) if ok else (height - 18)
        if ok:
            parts.append(
                f'<rect x="{x:.2f}" y="{y}" width="{bw:.2f}" height="{h}" rx="1.2" '
                f'fill="currentColor" style="opacity:0.85"/>'
            )
        else:
            parts.append(
                f'<rect x="{x:.2f}" y="{y}" width="{bw:.2f}" height="{h}" rx="1.2" '
                f'fill="var(--line)"/>'
            )
    parts.append('</svg>')
    return mark_safe(''.join(parts))


@register.filter(name='get_initials')
def get_initials(user):
    """Two-character initials for the avatar."""
    if not user:
        return '?'
    first = (user.first_name or user.username or '?')[:1]
    last = (user.last_name or '')[:1]
    return (first + last).upper() if last else first.upper()


@register.filter(name='last_user_sync')
def last_user_sync(user):
    """Return the datetime of the user's most recent successful SYNC, or None."""
    try:
        return Activity_log.objects.filter(action='SYNC', user_affected=user.username).latest('date').date
    except Activity_log.DoesNotExist:
        return None


@register.simple_tag(takes_context=True)
def path_without_lang(context):
    """Return the request path with any leading language prefix stripped.

    Used by the language picker as the `next` field so Django's set_language
    view redirects to a prefix-less URL; LocaleMiddleware then re-applies the
    just-chosen language. (Django's translate_url cannot rewrite the prefix
    on its own when the source URL's language differs from the active one.)
    """
    from django.utils.translation.trans_real import get_language_from_path
    path = context['request'].path
    lang = get_language_from_path(path)
    if lang:
        return path[len(lang) + 1:] or '/'
    return path


@register.filter(name='code_class')
def code_class(code):
    """Map dyndns2 return codes to a CSS class for the activity log pills."""
    if code == 'good':
        return 'code-good'
    if code == 'nochg':
        return 'code-info'
    if code in ('abuse', 'badagent'):
        return 'code-warn'
    return 'code-bad'
