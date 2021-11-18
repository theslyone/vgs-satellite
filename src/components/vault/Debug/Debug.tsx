import React, { useState, useEffect } from 'react';
import { Button, Card, Select, Row, Col } from 'src/components/antd';
import { getVaultBadge } from 'src/redux/utils/utils';
import { IVaultEssentials } from 'src/redux/interfaces/vault';
import { IEnvironment } from 'src/redux/interfaces/organization';

interface Props {
    handleCancel: () => void;
    handleOk: (vaultId: string) => void;
    getOrganizationEnvironments: (orgId: string) => any;
    isLoading: boolean;
    organizations: any[];
    environments: IEnvironment[];
    vaults: IVaultEssentials[];
}

const Debug: React.FC<Props> = (props) => {
    const {
        handleCancel,
        handleOk,
        getOrganizationEnvironments,
        isLoading,
        organizations,
        environments,
        vaults,
      } = props;
    
      const [selectedOrg, setSelectedOrg] = useState<string>();
      const [selectedVault, setSelectedVault] = useState<string>();
    
      useEffect(() => {
        if (!!organizations.length && !selectedOrg) {
          setSelectedOrg(organizations[0]?.id);
          getOrganizationEnvironments(organizations[0]?.id);
        }
      }, [organizations, selectedOrg]);
    
      useEffect(() => {
        if (!!vaults.length && selectedOrg && !selectedVault) {
          setSelectedVault(vaultsByOrg(selectedOrg)[0]?.identifier);
        }
      }, [vaults, selectedOrg, selectedVault]);
    
      const handleSelectOrg = (orgId: string) => {
        getOrganizationEnvironments(orgId);
        setSelectedOrg(orgId);
        setSelectedVault(undefined);
      };
    
      const vaultsByOrg = (orgId: string) =>
        vaults.filter((vault: IVaultEssentials) => vault.orgId === orgId)?.sort();

    return (
        <div className='d-flex justify-content-center'>
          <Card className='px-4 pt-2 pb-3 mt-5'>
            <h2 className='text-text text-lg _500'>Choose Organization & Vault</h2>
            <p>
              Please select the VGS organization and vault
              <br />
              into which you wish to promote your route
              <br />
              from VGS Satellite.
            </p>
            <p className='text-sm text-text-light mb-1'>Organization</p>
            <Select
              className='w-100'
              onSelect={handleSelectOrg}
              value={selectedOrg}
              disabled={!organizations.length}
            >
              {organizations.map((org: any) => (
                <Select.Option value={org.id} key={org.id}>
                  {org.name}
                </Select.Option>
              ))}
            </Select>
            <p className='text-sm text-text-light mb-1 mt-3'>Vault</p>
            <Select
              className='w-100'
              onSelect={setSelectedVault}
              value={selectedVault}
              disabled={!selectedOrg}
            >
              {!!selectedOrg &&
                vaultsByOrg(selectedOrg).map((vault: IVaultEssentials) => (
                  <Select.Option value={vault.identifier} key={vault.id}>
                    <span className="d-inline-flex align-items-center mr-2">
                      {getVaultBadge(environments, vault.environment)}
                    </span>
                    <span>{vault.name} ({vault.identifier})</span>
                  </Select.Option>
                ))}
            </Select>
            <Row gutter={16} className='mt-4'>
              <Col span={12}>
                <Button
                  ghost
                  onClick={handleCancel}
                  className='w-100'
                >
                  Cancel
                </Button>
              </Col>
              <Col span={12}>
                <Button
                  color='primary'
                  disabled={!selectedVault}
                  onClick={() => handleOk(selectedVault!)}
                  className='w-100'
                  loading={isLoading}
                >
                  {isLoading ? 'Waiting' : 'Debug'}
                </Button>
              </Col>
            </Row>
          </Card>
        </div>
      );
};

export default Debug;
