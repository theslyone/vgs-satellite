import React, { useEffect } from 'react';
import { connect } from 'react-redux';
import history from 'src/redux/utils/history';
import { initClient } from 'src/redux/modules/auth';
import { getOrganizationEnvironments } from 'src/redux/modules/organization';
import { fetchRoutes } from 'src/redux/modules/routes';
import config from 'src/config/config';
import { IRoute } from 'src/redux/interfaces/routes';
import { IVaultEssentials } from 'src/redux/interfaces/vault';
import { IEnvironment } from 'src/redux/interfaces/organization';
import Debug from './Debug';


const mapStateToProps = ({ auth, organization, vault, routes }: any) => {
    return {
      sessions: auth.sessions,
      organizations: organization.organizationsList,
      environments: organization.environments,
      vaults: vault.vaultsList,
      routes: routes.list,
    };
  };
  const mapDispatchToProps = {
    initClient,
    fetchRoutes,
    getOrganizationEnvironments,
  };

interface Props {
    // routeId: string;
    organizations: any[];
    environments: IEnvironment[];
    vaults: IVaultEssentials[];
    sessions: { [clientId: string]: any };
    routes: IRoute[];
    isPromoting: boolean;
    isMerging: boolean;
    initClient: (kcConfig: any, loginOptions?: any) => any;
    fetchRoutes: () => any;
    getOrganizationEnvironments: (orgId: string) => Promise<any>;
  }

const DebugContainer: React.FC<Props> = (props) => {
    const { sessions, organizations, environments, vaults, routes, isPromoting, isMerging } = props;
    const client = sessions[config.keycloakConfig.clientId];

    useEffect(() => {
        if (!client) {
          props.initClient(config.keycloakConfig, config.keycloakConfig);
        }
        props.fetchRoutes();
      }, [client]);

    const goDebug = () => console.log('will debug');
    
    return !client ? (
        <h2 className='text-text-light _300 text-center mt-5 text-lg'>
          Setting up the remote connection...
        </h2>
      ) : (
        <Debug
            handleCancel={() => history.push('/')}
            handleOk={goDebug}
            isLoading={false}
            organizations={organizations}
            vaults={vaults}
            environments={environments}
            getOrganizationEnvironments={props.getOrganizationEnvironments}
        />
    );
};

export default connect(
    mapStateToProps,
    mapDispatchToProps,
  )(DebugContainer);
