openerp.project_management = function (instance) {
    var _t = instance.web._t;
    _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    instance.web.project_management = instance.web.project_management || {};
    
    instance.project_management.test = instance.web.Class.extend({

    init:function() {
        var self = this;
        $(document).on('doSomePrinting()', this, function() {
        console.log("Event Executed Successfully");
        });
    
    },
    start:function() {
    $(document).ready(function () {
        
        if ($("#my_id")) {
            console.log("Hello Bitch");
            $(":button").text("Save").click(function () {
            console.log("Hello Bitch");
            });
        }
        console.log("Password Changed Successfully");        
        console.log("Password Changed Successfully");
        var mod = new instance.web.Model("project.task");
        console.log(mod);
        mod.call('trial_method',[]).then(function (result) { 
        console.log("Executed Successfully");
        });
    });
    },
});

var my_object = new instance.project_management.test();
my_object.start();

}

