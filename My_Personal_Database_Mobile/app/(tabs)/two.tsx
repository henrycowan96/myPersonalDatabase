import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { SettingsScreen } from '../../components/settings/SettingsScreen';
import { useIntegrations } from '../../components/settings/useIntegrations';

export default function SettingsPage() {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
    });
  }, []);

  const {
    integrations,
    loading,
    chainAnimations,
    toggleIntegration,
    handleLogout,
    handleClearData,
  } = useIntegrations(user);

  if (!user) {
    return null;
  }

  return (
    <SettingsScreen
      user={user}
      integrations={integrations}
      loading={loading}
      chainAnimations={chainAnimations}
      toggleIntegration={toggleIntegration}
      handleLogout={handleLogout}
      handleClearData={handleClearData}
    />
  );
}
