import React from 'react';
import { Route, Switch } from 'react-router-dom';
import { RouteComponentProps, withRouter } from 'react-router';
import Home from 'src/components/vault/Home/Home';
import PreCollectContainer from 'src/components/vault/PreCollect/PreCollectContainer';
import RoutesListContainer from 'src/components/vault/RoutesList/RoutesListContainer';
import RouteContainer from 'src/components/vault/Route/RouteContainer';
import NewRouteContainer from 'src/components/vault/Route/NewRouteContainer';
import PromoteRouteContainer from 'src/components/vault/PromoteRoute/PromoteRouteContainer';
import DebugContainer from 'src/components/vault/Debug/DebugContainer';

interface IAppSwitchProps {
}

const AppSwitch: React.FC<IAppSwitchProps> = (props) => {
  return (
    <>
      <ScrollToTop />
      <Switch>
        <Route exact path="/" component={Home}/>
        <Route exact path="/logs" component={PreCollectContainer}/>
        <Route
          exact
          path="/debugger"
          component={DebugContainer}
        />
        <Route exact path="/routes" component={RoutesListContainer}/>
        <Route
          exact
          path="/routes/:routeId/edit"
          render={(p) => <RouteContainer routeId={p.match.params.routeId} />}
        />
        <Route
          exact
          path="/routes/new/inbound"
          render={() => <NewRouteContainer routeType="inbound" />}
        />
        <Route
          exact
          path="/routes/new/outbound"
          render={() => <NewRouteContainer routeType="outbound" />}
        />
        <Route
          exact
          path="/routes/:routeId/promote"
          render={(p) => <PromoteRouteContainer routeId={p.match.params.routeId} />}
        />
        <Route component={Home}/>
      </Switch>
    </>
  );
};

export const ScrollToTop = withRouter(
  class ScrollToTopWithoutRouter extends React.Component<
    RouteComponentProps<any>,
    void
  > {
    componentDidUpdate(prevProps: Readonly<RouteComponentProps<any>>) {
      if (this.props.location !== prevProps.location) {
        window.scrollTo(0, 0);
      }
    }

    render(): JSX.Element {
      return null;
    }
  },
);

export default AppSwitch;
