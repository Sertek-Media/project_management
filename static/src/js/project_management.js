openerp.project_management = function (instance) {
    var _t = instance.web._t;
    var _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.project_management = instance.web.project_management || {};

    instance.project_management.WidgetMultiplication = instance.web.form.FormWidget.extend({
    
    init: function (field_manager, node) {
	    this._super(field_manager, node);
    },
	
	start:function() {
		 this._super();
		 var self = this;
		 $("button.oe_button.oe_form_button_save.oe_highlight").on('click',self,function(e) {
			 self.field_manager.on("field_changed:id",self,function() 
		    		{   
				 		if (self.view.datarecord.id && !self.get("effective_readonly")) 
		    				 {  
				 				if (self.field_manager.get("actual_mode") == "edit")
		    						{
				 							var mod = new instance.web.Model("project.task");
			    							mod.call('create_mail',[self.view.datarecord.id]).done(function(ctx) {
		    								var action = {};
									    	action = {
									             'type': 'ir.actions.act_window',
									             'view_type': 'form',
									             'res_id':ctx.wizard_id,
									             'view_mode': 'form',
									             'res_model': 'mail.compose.message',
									             'views': [[ctx.compose_form_id, 'form']],
									             'view_id': ctx.compose_form_id,
									             'target': 'new',
									             'context':ctx,
									               };
	   								    	 self.do_action(action);
			    							})
				                	    }
		    				 }
	    		});
		});
	},
	
});
instance.web.form.custom_widgets.add('multiplication', 'instance.project_management.WidgetMultiplication');

//	instance.project_management.TestWidget = instance.web.Widget.extend({
//		
//		dispatch_to_new_action: function() {
//			var self = this;
//	    	var mod1 = new instance.web.Model("project.task");
//	    	mod1.call('desc_pop_start',[287,{}]).done(function(ctx){
//			action = {
//		             'type': 'ir.actions.act_window',
//		             'view_type': 'form',
//		             'res_id':ctx.res_id, //ctx.res_id_id,
//		             'view_mode': 'form',
//		             'res_model': 'description.pop',
//		             'views': [[ctx.view_id, 'form']],
//		             'view_id': ctx.view_id,
//		             'target': 'new',
//		             'context':ctx,
//		               };
//			self.do_action(action);							
//			});
//	    },
//	});

	var module = instance.hr_attendance;
	module.AttendanceSlider.include({ 
        start: function() {
            var self = this;
            this._super();
			var callback = function(model,view){
				var mod1 = new instance.web.DataSet(self, 'ir.model.data');
				mod1.call('get_object_reference',['project_management',view]).then(function(view_id){
					action = { 
							'type': 'ir.actions.act_window',
				             'view_type': 'form',
				             'view_mode':'kanban',
				             'views':[[view_id[1],'kanban']],
				             'view_id':view_id[1],
				             'target':'current',
				             'res_model': model,
				               };
					instance.client.action_manager.do_action(action);
				});
			};

            var tmp = function() {
                var $sign_in_out_icon = this.$('#oe_attendance_sign_in_out_icon');
                $sign_in_out_icon.toggleClass("fa-sign-in", ! this.get("signed_in"));
                $sign_in_out_icon.toggleClass("fa-sign-out", this.get("signed_in"));
            };
            this.on("change:signed_in", this, tmp);
            _.bind(tmp, this)();
            this.$(".oe_attendance_sign_in_out").click(function(ev) {
                ev.preventDefault();
        		var mod = new instance.web.Model("project.task.time.recorder");
	        	mod.call('check_timer_stop',[]).then(function(result){
					if (result.type == 'clear'){
						location.reload();						
					}
					else if (result.type == 'task') {
//						self.obj = new instance.project_management.TestWidget(self);
//						self.obj.dispatch_to_new_action();
				    	result.source = "javascript";
				    	var mod1 = new instance.web.DataSet(self, 'project.task');
				    	mod1.call('desc_pop_start',[result.list_id,result]).done(function(ctx){
				    		ctx.context.active_model = 'project.task';
							ctx.context.active_ids = ctx.context.list_id; 
							ctx.context.resource = "task_javascript";					    		
							gctx = ctx;
							mod1.call('timer_state_stop',[result.list_id,ctx.context])
							action = {
						             'type': 'ir.actions.act_window',
						             'view_type': 'form',
						             'res_id':ctx.res_id,
						             'view_mode': 'form',
						             'res_model': ctx.res_model,
						             'views': [[ctx.view_id, 'form']],
						             'view_id': ctx.view_id,
						             'target': 'new',
						             'context':ctx.context,
						               };
							instance.client.action_manager.do_action(action).done(function(){
								$(document).keyup(function(e) {
									  if (e.keyCode == 27) {callback('project.task','change_project_task_kanban_view');}  //esc
									});	
								
								$('.close').on('click',function(e){
//success									location.reload(true);
//success									instance.webclient.notification.warn(_t("File upload"), "ddd");
//success web/controllers/main.py			self.rpc('/web/dataset/resequence', {
//										    model: 'project.task',
//										    ids: [287],
//										    field:'timer_state',
//										});
										callback('project.task','change_project_task_kanban_view');
								});
							});
				    	});
					}
					else{
						var mod1 = new instance.web.Model("project.issue");
				    	result.source = "issue_javascript";
						mod1.call('desc_pop_start',[result.list_id,result]).done(function(ctx){
							ctx.context.active_model = 'project.issue';
							ctx.context.active_ids = ctx.context.list_id; 
							ctx.context.resource = "issue_javascript";
							mod1.call('timer_state_stop',[result.list_id,ctx.context])
							action = {
						             'type': 'ir.actions.act_window',
						             'view_type': 'form',
						             'res_id':ctx.res_id,
						             'view_mode': 'form',
						             'res_model': ctx.res_model,
						             'views': [[ctx.view_id, 'form']],
						             'view_id': ctx.view_id,
						             'target': 'new',
						             'context':ctx.context,
						               };
							instance.client.action_manager.do_action(action);
							$(document).keyup(function(e) {
								  if (e.keyCode == 27) {callback('project.issue','change_project_issue_kanban_view');}  //esc
								});
							$("body").on('click',function(e){
								if ($(e.srcElement).hasClass("close")){
									callback('project.issue','change_project_issue_kanban_view');	
									}
								});
						});
					}
				});                
            });
            this.$el.tooltip({
                title: function() {
                    var last_text = instance.web.format_value(self.last_sign, {type: "datetime"});
                    var current_text = instance.web.format_value(new Date(), {type: "datetime"});
                    var duration = self.last_sign ? $.timeago(self.last_sign) : "none";
                    if (self.get("signed_in")) {
                        return _.str.sprintf(_t("Last sign in: %s,<br />%s.<br />Click to sign out."), last_text, duration);
                    } else {
                        return _.str.sprintf(_t("Click to Sign In at %s."), current_text);
                    }
                },
            });
            return this.check_attendance();
        },
	});
};