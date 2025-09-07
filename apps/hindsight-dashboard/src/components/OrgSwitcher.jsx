import React, { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { useOrg } from '../context/OrgContext';

const OrgSwitcher = () => {
  const { user, guest } = useAuth();
  const { organizations, activeScope, activeOrgId, setActiveScope, setActiveOrgId } = useOrg();

  const options = useMemo(() => {
    const base = [];
    if (guest) {
      base.push({ label: 'Public', value: 'public' });
      return base;
    }
    base.push({ label: 'Personal', value: 'personal' });
    for (const org of organizations) {
      base.push({ label: org.name, value: `org:${org.id}` });
    }
    return base;
  }, [guest, organizations]);

  const selectedValue = useMemo(() => {
    if (guest) return 'public';
    if (activeScope === 'organization' && activeOrgId) return `org:${activeOrgId}`;
    return 'personal';
  }, [guest, activeScope, activeOrgId]);

  const onChange = (e) => {
    const val = e.target.value;
    if (val === 'public') {
      setActiveScope('public');
      setActiveOrgId(null);
    } else if (val === 'personal') {
      setActiveScope('personal');
      setActiveOrgId(null);
    } else if (val.startsWith('org:')) {
      setActiveScope('organization');
      setActiveOrgId(val.substring(4));
    }
  };

  // Hide if not authenticated and not guest (loading handled elsewhere)
  if (!guest && (!user || !user.authenticated)) return null;

  return (
    <select
      className="border border-gray-300 rounded-md px-2 py-1 text-xs sm:text-sm bg-white"
      value={selectedValue}
      onChange={onChange}
      aria-label="Data scope"
      title="Data scope"
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
};

export default OrgSwitcher;

