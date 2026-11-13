import { useTranslation } from 'react-i18next'

import { isAccountStatus, isAuditOutcome, type AccountStatus, type AuditOutcome } from '../types/admin'
import { isRoleCode } from '../types/auth'

const BADGE = 'inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset'

/** Translated access-role names; unknown codes are shown as sent by the API. */
export function RoleChips({ roles }: { roles: readonly string[] }) {
  const { t } = useTranslation()
  if (roles.length === 0) {
    return <span className="text-sm text-slate-500">{t('auth.userMenu.noRoles')}</span>
  }
  return (
    <ul className="flex flex-wrap gap-1">
      {roles.map((code) => (
        <li key={code} className={`${BADGE} bg-brand-50 text-brand-800 ring-brand-200`}>
          {isRoleCode(code) ? t(`roles.${code}`) : code}
        </li>
      ))}
    </ul>
  )
}

const STATUS_TONE: Record<AccountStatus, string> = {
  active: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  pending_activation: 'bg-amber-50 text-amber-900 ring-amber-200',
  suspended: 'bg-orange-50 text-orange-900 ring-orange-200',
  disabled: 'bg-slate-100 text-slate-700 ring-slate-300',
}

export function AccountStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  if (!isAccountStatus(status)) {
    return <span className={`${BADGE} bg-slate-100 text-slate-700 ring-slate-300`}>{status}</span>
  }
  return <span className={`${BADGE} ${STATUS_TONE[status]}`}>{t(`userStatus.${status}`)}</span>
}

const OUTCOME_TONE: Record<AuditOutcome, string> = {
  success: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  failure: 'bg-red-50 text-red-800 ring-red-200',
  denied: 'bg-amber-50 text-amber-900 ring-amber-200',
}

export function OutcomeBadge({ outcome }: { outcome: string }) {
  const { t } = useTranslation()
  if (!isAuditOutcome(outcome)) {
    return <span className={`${BADGE} bg-slate-100 text-slate-700 ring-slate-300`}>{outcome}</span>
  }
  return <span className={`${BADGE} ${OUTCOME_TONE[outcome]}`}>{t(`audit.outcomes.${outcome}`)}</span>
}
