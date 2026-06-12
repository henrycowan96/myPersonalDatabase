import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { SettingsScreen } from '../../components/settings/SettingsScreen';
import { useIntegrations } from '../../components/settings/useIntegrations';
import LoadingScreen from '../../components/LoadingScreen';

export default function SettingsPage() {
  const [user, setUser] = useState<any>(null);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setInitialLoading(false);
    });
  }, []);

  const {
    integrations,
    loading,
    chainAnimations,
    toggleIntegration,
    handleLogout,
    handleClearData,
    handleDeleteAccount,
  } = useIntegrations(user);

  if (initialLoading) {
    return <LoadingScreen message="Loading settings..." subtext="Preparing your preferences" />;
  }

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
      handleDeleteAccount={handleDeleteAccount}
    />
  );
}
