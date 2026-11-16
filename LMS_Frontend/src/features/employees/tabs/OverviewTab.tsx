import { useTranslation } from 'react-i18next'

import { AccountStatusBadge } from '../../../components/Badges'
import { SUPPORTED_LANGUAGES } from '../../../i18n/languages'
import { formatDate, formatDateTime } from '../../../lib/format'
import { useProfile } from '../profileContext'
import { Detail, EmployeeLink, EmploymentStatusBadge, OrgPath } from '../EmployeeParts'

const PANEL = 'space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5'

/** Employee details and the organisational context on the selected date. */
export function OverviewTab() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const { employee } = useProfile()
  const date = (value: string | null) => (value ? formatDate(value, language) : t('emp.common.notRecorded'))
  const text = (value: string | null) => value ?? <span className="text-slate-500">{t('emp.common.notRecorded')}</span>

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section aria-labelledby="emp-details" className={PANEL}>
        <h2 id="emp-details" className="text-lg font-semibold text-slate-900">
          {t('emp.overview.details')}
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label={t('emp.fields.employeeCode')}>
            <span className="font-mono">{employee.employee_code}</span>
          </Detail>
          <Detail label={t('emp.fields.status')}>
            <EmploymentStatusBadge status={employee.employment_status} />
          </Detail>
          <Detail label={t('emp.fields.fullName')}>{employee.full_name}</Detail>
          <Detail label={t('emp.fields.displayName')}>{text(employee.display_name)}</Detail>
          <Detail label={t('emp.fields.preferredLanguage')}>
            {employee.preferred_language
              ? (SUPPORTED_LANGUAGES.find((item) => item.code === employee.preferred_language)?.nativeName ??
                employee.preferred_language)
              : text(null)}
          </Detail>
          <Detail label={t('emp.fields.workEmail')}>
            <span className="break-all">{text(employee.work_email)}</span>
          </Detail>
          <Detail label={t('emp.fields.dateOfJoining')}>{date(employee.date_of_joining)}</Detail>
          <Detail label={t('emp.fields.lastWorkingDay')}>
            {employee.date_of_separation ? formatDate(employee.date_of_separation, language) : t('emp.common.none')}
          </Detail>
          <Detail label={t('emp.fields.externalRef')}>{text(employee.external_ref)}</Detail>
          <Detail label={t('emp.overview.updated')}>
            {formatDateTime(employee.updated_at, language, { dateStyle: 'medium', timeStyle: 'short' })}
          </Detail>
        </dl>
      </section>

      <section aria-labelledby="emp-position" className={PANEL}>
        <h2 id="emp-position" className="text-lg font-semibold text-slate-900">
          {t('emp.overview.position', { date: formatDate(employee.as_of, language) })}
        </h2>
        <dl className="grid gap-4">
          <Detail label={t('emp.overview.primaryUnit')}>
            <OrgPath path={employee.path} unit={employee.primary_unit} />
          </Detail>
          <Detail label={t('emp.fields.designation')}>{text(employee.designation?.name ?? null)}</Detail>
          <Detail label={t('emp.fields.location')}>{text(employee.location?.name ?? null)}</Detail>
          <Detail label={t('emp.overview.lineManager')}>
            {employee.line_manager ? <EmployeeLink employee={employee.line_manager} /> : t('emp.common.none')}
          </Detail>
        </dl>
        <p className="text-xs text-slate-600">{t('emp.overview.positionNote')}</p>
      </section>

      <section aria-labelledby="emp-accounts" className={`${PANEL} lg:col-span-2`}>
        <h2 id="emp-accounts" className="text-lg font-semibold text-slate-900">
          {t('emp.overview.accounts')}
        </h2>
        {employee.accounts.length === 0 ? (
          <p className="text-sm text-slate-600">{t('emp.account.none')}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {employee.accounts.map((account) => (
              <li key={account.public_id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
                <span className="font-mono text-slate-900">{account.login_id}</span>
                <span className="text-slate-700">{account.display_name}</span>
                <AccountStatusBadge status={account.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
