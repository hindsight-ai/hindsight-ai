import React, { useState } from 'react';
import { CreateOrganizationData } from '../api/organizationService';

interface OrganizationEditPanelProps {
  onSubmit: (data: CreateOrganizationData) => Promise<void>;
  onCancel: () => void;
}

const OrganizationEditPanel: React.FC<OrganizationEditPanelProps> = ({ onSubmit, onCancel }) => {
  const [newOrgData, setNewOrgData] = useState<CreateOrganizationData>({ name: '', slug: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(newOrgData);
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4 p-3 border rounded bg-gray-50">
      <div className="mb-2">
        <input
          type="text"
          placeholder="Organization Name"
          value={newOrgData.name}
          onChange={(e) => setNewOrgData({ ...newOrgData, name: e.target.value })}
          className="w-full px-2 py-1 border rounded text-sm"
          required
        />
      </div>
      <div className="mb-2">
        <input
          type="text"
          placeholder="Slug (optional)"
          value={newOrgData.slug}
          onChange={(e) => setNewOrgData({ ...newOrgData, slug: e.target.value })}
          className="w-full px-2 py-1 border rounded text-sm"
        />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="bg-green-500 text-white px-2 py-1 rounded text-sm hover:bg-green-600">
          Create
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="bg-gray-500 text-white px-2 py-1 rounded text-sm hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};

export default OrganizationEditPanel;
