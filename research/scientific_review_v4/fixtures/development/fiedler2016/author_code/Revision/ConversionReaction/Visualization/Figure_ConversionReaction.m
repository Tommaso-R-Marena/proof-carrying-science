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

%% Figure 2.2
clc; close all; clearvars -except 'setLay'

% print
printBoolean = true;

% set figure properties
close all;
fig = figure(1);
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
cur_dir = strrep(which('Figure_ConversionReaction'),'Figure_ConversionReaction.m','');
eval(['cd ' cur_dir]);

load('../Results/ResultManuscriptConversionReaction.mat')
%%
theta_min_vec = repmat(theta_real',1,max([length(Theta_MS{2,i}(:,1)),...
    length(Theta_MS{1,i}(:,1)),length(Theta_MS{3,i}(:,1))]));

X_s2 = x_s([Theta_MS{2,i}(:,1)';Theta_MS{2,i}(:,2)'],us);
X_s1 = x_s([Theta_MS{1,i}(:,1)';Theta_MS{1,i}(:,2)'],us);
X_s3 = x_s([Theta_MS{3,i}(:,1)';Theta_MS{3,i}(:,2)'],us);
%% plot results
cmp = colormap(parula(6));
colvec = cmp;
colvecSD = colvec;
clear cmp

i=1;
subplot(ha(1))   
   lh(1) = surf(Theta_1,Theta_2,Xs,log(Js)); 
   colormap gray(200); 
   shading interp;
   hold on;

    % plot solver paths
    lh(2)=plot3(Theta_MS{1,i}(:,1),Theta_MS{1,i}(:,2),X0_MS{1,i},'Color',colvec(1,:)); hold on;%,
    lh(3)=plot3(Theta_MS{2,i}(:,1),Theta_MS{2,i}(:,2),X0_MS{2,i},'Color',colvec(2,:)); %
    lh(4)=plot3(Theta_MS{3,i}(:,1),Theta_MS{3,i}(:,2),X0_MS{3,i},'Color',colvec(4,:)); %

    % plot solver result
    plot3(Theta_MS{1,i}(end,1),Theta_MS{1,i}(end,2),X0_MS{1,i}(end),'*','Color',colvec(1,:));
    plot3(Theta_MS{2,i}(end,1),Theta_MS{2,i}(end,2),X0_MS{2,i}(end),'*','Color',colvec(2,:));
    plot3(Theta_MS{3,i}(end,1),Theta_MS{3,i}(end,2),X0_MS{3,i}(end),'*','Color',colvec(4,:));
    
    plot3(theta_real(1),theta_real(2),xs_real,'*r','Markersize',10);

    % indicate solver path direction
    plot3(Theta_MS{1,i}(round(end/4),1),Theta_MS{1,i}(round(end/4),2),...
        X0_MS{1,i}(round(end/4)),'^','Color',colvec(1,:),'MarkerFaceColor',colvec(1,:),'Markersize',3);
    plot3(Theta_MS{2,i}(round(end/4),1),Theta_MS{2,i}(round(end/4),2),...
        X0_MS{2,i}(round(end/4)),'^','Color',colvec(2,:),'MarkerFaceColor',colvec(2,:),'Markersize',3);
    plot3(Theta_MS{3,i}(round(end/3.5),1),Theta_MS{3,i}(round(end/3.5),2),...
        X0_MS{3,i}(round(end/3.5)),'^','Color',colvec(4,:),'MarkerFaceColor',colvec(4,:),'Markersize',3);

    xlabel('parameter \theta_1','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    hly = ylabel('parameter \theta_2','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    zlabel('steady state x_s','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(hly,'Position',[0,1,-0.05])

    view(-12,5);
    xlim([0.9,8])
    ylim([-0.1,1.8])
    zlim([0,0.6])
    set(gca,'Fontsize',8);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(2))   
   lh2(1)= plot(theta_min_vec(1,:),':','Color',[0.4,0.4,0.4]); hold on;
    box on
    % plot theta_1 path 
    plot(Theta_MS{1,i}(:,1),'Color',colvec(1,:)); 
    plot(Theta_MS{2,i}(:,1),'Color',colvec(2,:));
    plot(Theta_MS{3,i}(:,1),'Color',colvec(4,:));

    % plot theta_1 path end
    plot(length(Theta_MS{1,i}(:,1)),Theta_MS{1,i}(end,1),'*','Color',colvec(1,:));
    plot(length(Theta_MS{2,i}(:,1)),Theta_MS{2,i}(end,1),'*','Color',colvec(2,:));
    plot(length(Theta_MS{3,i}(:,1)),Theta_MS{3,i}(end,1),'*','Color',colvec(4,:));

    ylabel('parameter \theta_1','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)])
    ylim([2 8])
    set(gca,'Fontsize',8)
    
subplot(ha(3))   
    % plot optimal theta_2
    plot(theta_min_vec(2,:),':','Color',[0.4,0.4,0.4]);
    hold on
    box on
    
    % plot theta_2 path
    plot(Theta_MS{1,i}(:,2),'Color',colvec(1,:));
    plot(Theta_MS{2,i}(:,2),'Color',colvec(2,:));
    plot(Theta_MS{3,i}(:,2),'Color',colvec(4,:));

    % plot theta_2 path end
    plot(length(Theta_MS{1,i}(:,2)),Theta_MS{1,i}(end,2),'*','Color',colvec(1,:));
    plot(length(Theta_MS{2,i}(:,2)),Theta_MS{2,i}(end,2),'*','Color',colvec(2,:));
    plot(length(Theta_MS{3,i}(:,2)),Theta_MS{3,i}(end,2),'*','Color',colvec(4,:));

    ylabel('parameter \theta_2','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)])
    ylim([0.4 2])
    box on
    set(ha(3),'YTick',[0.6,1,1.4,1.8],'Boxstyle','full')
    set(gca,'Fontsize',8);


subplot(ha(4))   
    lh2(2) = plot(abs(X_s1-X0_MS{1,i}'),'Color',colvec(1,:));
    hold on
    box on
    lh2(3) = plot(abs(X_s2-X0_MS{2,i}'),'Color',colvec(2,:));
    lh2(4) = plot(abs(X_s3-X0_MS{3,i}'),'Color',colvec(4,:));
     
    xlabel('iterations','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    ylabel({'distance to analytical'; 'steady state'},'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    xlim([0 size(theta_min_vec,2)])

    set(gca,'Fontsize',8)
   

%% legend
hlf = legend(ha(1),lh,'steady-state manifold','solver path \lambda=0',...
    'solver path \lambda=1','solver path \lambda=10');
    set(hlf,'box','off','Position',[0.15, 0.06, 0.10, 0.06],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

hlf = legend(ha(2),lh2(1),'optimal parameter \theta_i^*');
    set(hlf,'box','off','Position',[0.45, 0.06, 0.10, 0.06],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

% save PDF of Figure
feval('print', '-dpdf','-r300','FigureCR.pdf');
