%% Set-up
clear all; close all; 
clc

% page size
setLay.txt.width = 20.4; % breite max Bild (A4?)
setLay.txt.height = 29.1;

% font  
setLay.tit.size = 10;
setLay.tit.font = 'Times New Roman';
setLay.tit.weight = 'normal';

setLay.lab.size = 14;
setLay.lab.font = 'Helvetica';
setLay.lab.weight = 'bold';

setLay.ax.size = 10;
setLay.ax.font = 'Times New Roman';

% tight_subplot notation:
% ha = tight_subplot(Nh, Nw, [gap_h gap_w], [marg_h_lower margin_h_upper], [marg_w_left margin_w_right])

%% Figure 2.2
clc; close all; clearvars -except 'setLay'

% set figure properties
close all;
fig = figure(1);
%f_width = setLay.txt.width;
f_width = 0.9*setLay.txt.width;
f_height = 0.5*setLay.txt.height;
set(fig,'Color',[1 1 1],...
        'Units','centimeters',...
        'Position', [0,0,f_width,f_height],...
        'PaperSize',[f_width f_height],...
        'PaperPosition', [0,0,f_width f_height],...
        'PaperSize', [f_width f_height])

% create axis
h = axes('Position',[0 0 1 1],'Visible','off');

% subfigure numbering
text(.01,0.98,'A','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.98,'B','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.655,'C','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.33,'D','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);

ha(1) = axes('Position', [0.1, 0.25, 0.55, 0.65]);
ha(2) = axes('Position', [0.74, 0.71, 0.22, 0.25]);
ha(3) = axes('Position', [0.74, 0.385, 0.22, 0.25]);
ha(4) = axes('Position', [0.74, 0.06, 0.22, 0.25]);

%% load data
cur_dir = strrep(which('Figure_ConversionReactionFMs'),'Figure_ConversionReactionFMs.m','');
eval(['cd ' cur_dir]);

load('../Results/ResultManuscriptConversionReaction.mat')
%%
i=1;
theta1Evol = [];
theta2Evol = [];
for k = 1:length(parameters_FMs.MS.evol{i}(1,2:end))/2-2
    theta1Evol = [theta1Evol,linspace(parameters_FMs.MS.evol{i}(1,2*k),parameters_FMs.MS.evol{i}(1,2*k+1),10)];
    theta2Evol = [theta2Evol,linspace(parameters_FMs.MS.evol{i}(2,2*k),parameters_FMs.MS.evol{i}(2,2*(k+1)),10)];
end
    xs_FMs = x_s([theta1Evol;theta2Evol],us);

theta_min_vec = repmat(theta_real',1,length(parameters_FMs.MS.evol{i}(1,:)));

X_s4 = x_s([parameters_FMs.MS.evol{i}(1,:);parameters_FMs.MS.evol{i}(2,:)],us);

col_vec = colormap(lines(5));

%% plot results

i=1;   
subplot(ha(1))   
   lh(1) = surf(Theta_1,Theta_2,Xs,log(Js)); shading interp; colormap gray(200); hold on
 
    % plot solver paths
     lh(2)=plot3(parameters_FMs.MS.evol{i}(1,:),parameters_FMs.MS.evol{i}(2,:),parameters_FMs.MS.evol{i}(3,:),'Color',col_vec(5,:));
    plot3(parameters_FMs.MS.evol{i}(1,2:2:end),parameters_FMs.MS.evol{i}(2,2:2:end),parameters_FMs.MS.evol{i}(3,2:2:end),'.','Color',col_vec(5,:),'Markersize',5);

    % plot solver result
    plot3(parameters_FMs.MS.evol{i}(1,end),parameters_FMs.MS.evol{i}(2,end),parameters_FMs.MS.evol{i}(3,end),'*','Color',col_vec(5,:),'Markersize',6);
    plot3(theta_real(1),theta_real(2),xs_real,'*r','Markersize',10);

    xlabel('parameter \theta_1','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    hly = ylabel('parameter \theta_2','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    zlabel('steady state x_s','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(hly,'Position',[1.3 1.5 -0.05])

    view(-12,5);
    xlim([1.6,4.5])
    ylim([-0.1,1.8])
    zlim([0,0.6])
    
    set(gca,'Fontsize',8);
    set(gcf,'renderer','opengl');
    %%
subplot(ha(2)) 
   lh2(1)= plot(0:length(parameters_FMs.MS.evol{i}(1,2:2:end))-1,theta_min_vec(1,2:2:end),':','Color',[0.4,0.4,0.4]); hold on;

    % plot theta_1 path 
    plot(0:length(parameters_FMs.MS.evol{i}(1,2:2:end))-1,parameters_FMs.MS.evol{i}(1,2:2:end),'Color',col_vec(5,:));

    % plot theta_1 path end
    plot(length(parameters_FMs.MS.evol{i}(1,:))/2-1,parameters_FMs.MS.evol{i}(1,end),'*','Color',col_vec(5,:));

    ylabel('parameter \theta_1','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)/2-1+0.01])
    ylim([2 5])
    box on;
    
    set(ha(2),'Boxstyle','full')
    set(gca,'Fontsize',8)
    
subplot(ha(3))
    box on
    % plot optimal theta_2
    plot(0:length(parameters_FMs.MS.evol{i}(1,2:2:end))-1,theta_min_vec(2,2:2:end),':','Color',[0.4,0.4,0.4]);
    hold on
    % plot theta_2 path
    plot(0:length(parameters_FMs.MS.evol{i}(1,2:2:end))-1,parameters_FMs.MS.evol{i}(2,2:2:end),'Color',col_vec(5,:));
   

    % plot theta_2 path end
    plot(length(parameters_FMs.MS.evol{i}(2,:))/2-1,parameters_FMs.MS.evol{i}(2,end),...
        '*','Color',col_vec(5,:));

    ylabel('parameter \theta_2','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)/2-1+0.01])
    ylim([0.2 1.6])
    
    set(gca,'Fontsize',8);


subplot(ha(4))  
    box on

    lh2(2) = plot(0:length(parameters_FMs.MS.evol{i}(1,2:2:end))-1,abs(X_s4(2:2:end)-parameters_FMs.MS.evol{i}(3,2:2:end)),'Color',col_vec(5,:));

    xlabel('iterations','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    ylabel({'distance to analytical'; 'steady state'},'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)/2-1+0.01])

    set(gca,'Fontsize',8)

%% legend
hlf = legend(ha(1),lh,'steady-state manifold','solver path');
    set(hlf,'box','off','Position',[0.15, 0.06, 0.10, 0.06],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

hlf2 = legend(ha(2),lh2(1),'optimal parameter \theta_i^*'); %,{'distance to analytical steady-state';'|x_s-x_s(\theta)|'}
    set(hlf2,'box','off','Position',[0.45, 0.06, 0.10, 0.06],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

% save PDF of Figure
feval('print', '-dpdf','-r300','FigureCRFMs.pdf');
