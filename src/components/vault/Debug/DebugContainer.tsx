import React, { useEffect, useState } from 'react';
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
import Editor from 'src/components/vault/Debug/Editor';


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

  const [sourceCode, setSourceCode] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [path, setPath] = useState('');
  const [threadId, setThreadId] = useState('');
  
  const getSessionId = async () => {
    const url = new URL('http://localhost:8089/debug');
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json;charset=utf-8'
      },
      body: JSON.stringify({
        org_id: 'ACmEie3BQ7MyKfokj7gbvdtA',
        vault: 'tntq89yyga5',
      })
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    const result = await response.json();
    console.log('result: ', result);

    if (result.error) {
      console.log(result.error.message);
    }

    return result.id;
  };

    const getSessionState = async (sessionId: string) => {
      const url = new URL(`http://localhost:8089/debug/${sessionId}`);
      const response = await fetch(url);
      const result = await response.json();
      console.log('retrieveDebugSession: ', result);
      return result?.state;
      
    };

    const retrieveThreads = async (sessionId: string) => {
      const url = new URL(`http://localhost:8089/debug/${sessionId}/threads`);
      const response = await fetch(url);
      const result = await response.json();
      console.log('retrieveThreads: ', result);
      return result;
    };

    const retrieveFrames = async (sessionId: string, threadId: string) => {
      const url = new URL(`http://localhost:8089/debug/${sessionId}/threads/${threadId}/frames`);
      const response = await fetch(url);
      const result = await response.json();

      return result;
    };

    const getSourceCode = async (path: string) => {
      const url = new URL(`http://localhost:8089/debug/source${path}`);
      const response = await fetch(url);
      const result = await response;

      return result;
    };

    const retrieveDebugSession = async () => {
      const sessionId = await getSessionId();
      setSessionId(sessionId);
      let sessionState = await getSessionState(sessionId);
      if (sessionState === 'INITIALIZING') {
        await new Promise(resolve => setTimeout(resolve, 2000));
        sessionState = await getSessionState(sessionId);
      }
      if (sessionState === 'RUNNING') {
        const threads = await retrieveThreads(sessionId);
        console.log('threads: ', threads);
        return threads?.threads;
      }
      console.log('sessionState: ', sessionState);
    };

    const goDebug = async () => {
      const threads = await retrieveDebugSession();
      console.log('threads: ', threads);

      const path = threads?.[0].location?.path;
      const threadId = threads?.[0]?.id;

      setPath(path);
      setThreadId(threadId);

      const response = await getSourceCode(path);
      const result = await response.text();

      console.log('sourceCode: ', result);
      setSourceCode(result);
    };

    if (!client) {
      return (
        <h2 className='text-text-light _300 text-center mt-5 text-lg'>
          Setting up the remote connection...
        </h2>
      );
    }

    if (sourceCode) {
      return (
        <Editor sourceCode={sourceCode} sessionId={sessionId} selectedFile={path} threadId={threadId} />
      );
    }
    
    return (
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
