dev.utils.clusterSetupDialog = {
  wasRun: false,
  prefill: function(){
    if(dev.utils.clusterSetupDialog.wasRun){
      return;
    }
    dev.utils.clusterSetupDialog.wasRun = true;
    clusterSetup.dialog.create();
    $('input[name^="clustername"]').val("starbug8");
    $('#create_new_cluster input[name="node-1"]').val("dave8");
    $('#create_new_cluster input[name="node-2"]').val("kryten8");
    $('#create_new_cluster input[name="node-3"]').val("holly8");
  },
};

dev.patch.ajax_wrapper(
  function(url){
    switch(url){
      case "/clusters_overview":
        if(dev.flags.cluster_overview_run === undefined){
          dev.flags.cluster_overview_run = true;
          console.group('Wrapping ajax_wrapper');
          console.log(url);
          console.groupEnd();
          return mock.clusters_overview;
        }
      default: return undefined;
    }
  },
  dev.utils.clusterSetupDialog.prefill,
);

testClusterSetup = {};

testClusterSetup.successPath = function(url, data, success, fail){
  switch(url){
    case "/manage/check_auth_against_nodes": return success(JSON.stringify({
      dave8: "Online",
      kryten8: "Online",
      holly8: "Online",
    }));
    case "/manage/send-known-hosts-to-node": return success("success");

    case "/manage/cluster-setup": return success(
      JSON.stringify(dev.fixture.success)
    );

    case "/manage/remember-cluster": return success();
  }
};

testClusterSetup.checkAuth500 = function(url, data, success, fail){
  switch(url){
    case "/manage/check_auth_against_nodes": return fail(
      500, "Somethig is wrong",
    );
    case "/manage/send-known-hosts-to-node": return success("success");
  }
};

testClusterSetup.checkAuthFails = function(url, data, success, fail){
  switch(url){
    case "/manage/check_auth_against_nodes": return fail();
  }
};

testClusterSetup.checkAuthNodesNotAuth = function(url, data, success, fail){
  switch(url){
    case "/manage/check_auth_against_nodes": return success(JSON.stringify({
      dave8: "Online",
      kryten8: "Unable to authenticate",
      holly8: "Cant connect",
    }));
  }
};

testClusterSetup.sendKnownHosts403 = function(url, data, success, fail){
  switch(url){
    case "/manage/send-known-hosts-to-node": return fail(
      403, "Permission denied."
    );
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.sendKnownHostsFail = function(url, data, success, fail){
  switch(url){
    case "/manage/send-known-hosts-to-node": return success("error");
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.sendKnownHostsUnsupported = function(url, data, success, fail){
  switch(url){
    case "/manage/send-known-hosts-to-node": return success("not_supported");
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.sendKnownHostsUnknownFail = function(url, data, success, fail){
  switch(url){
    case "/manage/send-known-hosts-to-node": return success("unknown");
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.clusterSetup403 = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup": return fail(
      403, "Permission denied."
    );
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.clusterSetup500 = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup": return fail(
      500, "Somethig is wrong",
    );
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};
testClusterSetup.clusterSetupUnforcible = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup": return success(
      JSON.stringify(dev.fixture.libErrorUnforcibleLarge)
    );
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.clusterSetupException = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup":
      return success(JSON.stringify(dev.fixture.libException));
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};


testClusterSetup.clusterSetupForceFail = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup":
      return success(JSON.stringify(
        dev.fixture.libError(JSON.parse(data.setup_data).force_flags.length < 1)
      ));
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.clusterSetupForceFailForcible = function(
  url, data, success, fail
){
  switch(url){
    case "/manage/cluster-setup":
      return success(JSON.stringify(dev.fixture.libError(true)));
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.clusterSetupForce = function(url, data, success, fail){
  switch(url){
    case "/manage/cluster-setup":
      if (JSON.parse(data.setup_data).force_flags.length < 1) {
        return success(JSON.stringify(dev.fixture.libError(true)));
      }
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};

testClusterSetup.rememberFail = function(url, data, success, fail){
  switch(url){
    case "/manage/remember-cluster": return fail(500, "Server error");
    default:
      return testClusterSetup.successPath(url, data, success, fail);
  }
};



dev.runScenario(
  // testClusterSetup.checkAuthFails
  // testClusterSetup.checkAuthNodesNotAuth
  // testClusterSetup.sendKnownHosts403
  // testClusterSetup.sendKnownHostsFail
  // testClusterSetup.sendKnownHostsUnsupported
  // testClusterSetup.sendKnownHostsUnknownFail
  // testClusterSetup.clusterSetup403
  // testClusterSetup.clusterSetup500
  // testClusterSetup.clusterSetupUnforcible
  // testClusterSetup.clusterSetupException
  // testClusterSetup.clusterSetupForceFail
  // testClusterSetup.clusterSetupForceFailForcible
  // testClusterSetup.clusterSetupForce
  // testClusterSetup.rememberFail
  testClusterSetup.successPath
);
