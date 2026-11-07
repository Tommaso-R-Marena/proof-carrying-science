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

%% Figure 5.2: Pom1p data
clc; close all; clearvars -except 'setLay'

% print
printBoolean = true;

% set figure properties
close all;
fig = figure(1);
f_width = 0.9*setLay.txt.width;
f_height = 0.75*setLay.txt.height;
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
text(.45,0.98,'B','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.98,'C','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.57,'D','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.69,0.28,'E','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);

text(.02,0.91,'unconstrained','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.89,'optimization','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.87,'fmincon','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(.02,0.72,'constrained','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.7,'optimization','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.68,'fmincon','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(.02,0.54,'hybrid','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.52,'method','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.5,'fmincon','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(.02,0.36,'simulation','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.34,'based','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.32,'gradient','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(.02,0.30,'descent','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(.02,0.18,'simulation','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.16,'based','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(.02,0.14,'newton-type','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.45,0.80,'solver indicates','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.465,0.81,'convergence','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.485,0.81,'no','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.485,0.875,'yes','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.49,0.96,'difference to analytical','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.525,0.945,'solution small','FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.53,0.93,'yes','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.61,0.93,'no','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.45,0.435,'solver indicates','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.465,0.445,'convergence','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.485,0.445,'no','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.485,0.51,'yes','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.53,0.7475,'yes','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.61,0.7475,'no','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.45,0.6175,'solver indicates','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.465,0.6275,'convergence','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.485,0.6275,'no','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.485,0.6925,'yes','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.53,0.565,'yes','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.61,0.565,'no','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.45,0.2525,'solver indicates','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.465,0.2625,'convergence','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.485,0.2625,'no','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.485,0.3275,'yes','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.53,0.3825,'yes','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.61,0.3825,'no','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.45,0.07,'solver indicates','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.465,0.08,'convergence','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight);
text(0.485,0.08,'no','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.485,0.145,'yes','Rotation',90,'FontName',setLay.ax.font,'FontSize',setLay.ax.size);

text(0.53,0.20,'yes','FontName',setLay.ax.font,'FontSize',setLay.ax.size);
text(0.61,0.20,'no','FontName',setLay.ax.font,'FontSize',setLay.ax.size);

%%
ha(1) = axes('Position', [0.19, 0.79, 0.22, 0.17]);
ha(2) = axes('Position', [0.19, 0.6075, 0.22, 0.17]);
ha(3) = axes('Position', [0.19, 0.425, 0.22, 0.17]);
ha(4) = axes('Position', [0.19, 0.2425, 0.22, 0.17]);
ha(5) = axes('Position', [0.19, 0.06, 0.22, 0.17]);

ha(6) = axes('Position', [0.505, 0.86, 0.07, 0.06]);
ha(13) = axes('Position', [0.585, 0.86, 0.07, 0.06]);
ha(14) = axes('Position', [0.505, 0.79, 0.07, 0.06]);
ha(15) = axes('Position', [0.585, 0.79, 0.07, 0.06]);

ha(7) = axes('Position', [0.505, 0.6775, 0.07, 0.06]);
ha(16) = axes('Position', [0.585, 0.6775, 0.07, 0.06]);
ha(17) = axes('Position', [0.505, 0.6075, 0.07, 0.06]);
ha(18) = axes('Position', [0.585, 0.6075, 0.07, 0.06]);

ha(8) = axes('Position', [0.505, 0.495, 0.07, 0.06]);
ha(19) = axes('Position', [0.585, 0.495, 0.07, 0.06]);
ha(20) = axes('Position', [0.505, 0.425, 0.07, 0.06]);
ha(21) = axes('Position', [0.585, 0.425, 0.07, 0.06]);

ha(9) = axes('Position', [0.505, 0.3125, 0.07, 0.06]);
ha(22) = axes('Position', [0.585, 0.3125, 0.07, 0.06]);
ha(23) = axes('Position', [0.505, 0.2425, 0.07, 0.06]);
ha(24) = axes('Position', [0.585, 0.2425, 0.07, 0.06]);

ha(10) = axes('Position', [0.505, 0.13, 0.07, 0.06]);
ha(25) = axes('Position', [0.585, 0.13, 0.07, 0.06]);
ha(26) = axes('Position', [0.505, 0.06, 0.07, 0.06]);
ha(27) = axes('Position', [0.585, 0.06, 0.07, 0.06]);

ha(11) = axes('Position',[0.72, 0.60, 0.23, 0.36]);

ha(12) = axes('Position',[0.74, 0.38, 0.21, 0.18]);

ha(28) = axes('Position',[0.74, 0.06, 0.21, 0.21]);

%%
cmp = colormap(lines(6));

% path
cur_dir = strrep(which('Figure_NGFInducedErkSignaling'),'Figure_NGFInducedErkSignaling.m','');
eval(['cd ' cur_dir]);

% load data
load('../Results/ResultManuscriptMS100_SDNM.mat')
load('../Results/ResultManuscriptMS100_FM.mat')
load('../Results/ResultManuscriptMS100_FMs.mat')
load('../Results/ResultManuscriptMS100_FUa.mat')

ind_lambda = 2;
sortConverged
%% plot SD
    
% Color SD - cmp(3,:)
colorind = 3;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
j=ind_lambda;
colvec = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];
colvecSD = colvec;
subplot(ha(9))   
    hold on
    fill([0,1,1,0],[0,0,percentSD(j,1),percentSD(j,1)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(9),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentSD(j,1)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(22))   
    hold on
    fill([0,1,1,0],[0,0,percentSD(j,2),percentSD(j,2)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(22),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentSD(j,2)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(23))   
    hold on
    fill([0,1,1,0],[0,0,percentSD(j,3),percentSD(j,3)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(23),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentSD(j,3)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(24))   
    hold on
    fill([0,1,1,0],[0,0,percentSD(j,4),percentSD(j,4)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(24),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentSD(j,4)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(4))
    plot(- parameters_SD{j}.MS.logPost(indSD(j,:)),'-o','Color',colvec(4,:),'MarkerSize',4);
    hold on
    plot(convABSD{j},- parameters_SD{j}.MS.logPost(indSD(j,convABSD{j})),'o','Color',colvec(1,:),'MarkerSize',4);
    plot(1:100,-bound*ones(100,1),':k')
    box on;
    ylim([0 60])
    
    
%% plot NM
colorind = 4;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));

colvecNM = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

subplot(ha(10))   
    hold on
    fill([0,1,1,0],[0,0,percentNM(j,1),percentNM(j,1)],colvecNM(2,:));
    ylim([0 100]);
    box on;
    set(ha(9),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentNM(j,1)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(25))   
    hold on
    fill([0,1,1,0],[0,0,percentNM(j,2),percentNM(j,2)],colvecNM(4,:));
    ylim([0 100]);
    box on;
    set(ha(25),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentNM(j,2)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(26))   
    hold on
    fill([0,1,1,0],[0,0,percentNM(j,3),percentNM(j,3)],colvecNM(2,:));
    ylim([0 100]);
    box on;
    set(ha(26),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentNM(j,3)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(27))   
    hold on
    fill([0,1,1,0],[0,0,percentNM(j,4),percentNM(j,4)],colvecNM(4,:));
    ylim([0 100]);
    box on;
    set(ha(27),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentNM(j,4)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(5))
    plot(-parameters_NM{j}.MS.logPost(indNM(j,:)),'-o','Color',colvecNM(4,:),'MarkerSize',4);
    hold on
    plot(convABNM{j},- parameters_NM{j}.MS.logPost(indNM(j,convABNM{j})),'o','Color',colvecNM(2,:),'MarkerSize',4);
    plot(1:100,-bound*ones(100,1),':k')
    ylim([0 60])
   

%% plot FMs
colorind = 5;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));

colvec = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

subplot(ha(8))   
    hold on
    fill([0,1,1,0],[0,0,percentFMs(1),percentFMs(1)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(8),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentFMs(1)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(19))   
    hold on
    fill([0,1,1,0],[0,0,percentFMs(2),percentFMs(2)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(19),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentFMs(2)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(20))   
    hold on
    fill([0,1,1,0],[0,0,percentFMs(3),percentFMs(3)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(20),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.4,50,[num2str(percentFMs(3)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(21))   
    hold on
    fill([0,1,1,0],[0,0,percentFMs(4),percentFMs(4)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(21),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.4,50,[num2str(percentFMs(4)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(3))
    hold on
    plot(-parameters_FMs.MS.logPost(indFMs),'-o','Color',colvec(4,:),'MarkerSize',4);
    plot(convABFMs,-parameters_FMs.MS.logPost(indFMs(convABFMs)),'o','Color',colvec(1,:),'MarkerSize',4);
    plot(convAFMs,-parameters_FMs.MS.logPost(indFMs(convAFMs)),'o','Color',colvec(1,:),'MarkerSize',4);
    plot(1:100,-bound*ones(100,1),':k')
    ylim([0 60])
    box on
    
 
%% plot FM    
colorind = 2;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));

colvec = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];
subplot(ha(7))   
    hold on
    fill([0,1,1,0],[0,0,percentFM(1),percentFM(1)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(7),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,40,[num2str(percentFM(1)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(16))   
    hold on
    fill([0,1,1,0],[0,0,percentFM(2),percentFM(2)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(16),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentFM(2)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(17))   
    hold on
    fill([0,1,1,0],[0,0,percentFM(3),percentFM(3)],colvec(1,:));
    ylim([0 100]);
    box on;
    set(ha(17),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentFM(3)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(18))   
    hold on
    fill([0,1,1,0],[0,0,percentFM(4),percentFM(4)],colvec(4,:));
    ylim([0 100]);
    box on;
    set(ha(18),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.3,50,[num2str(percentFM(4)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(2))
    plot(-parameters_FM.MS.logPost(indFM),'-o','Color',colvec(4,:),'MarkerSize',4);
    hold on
    plot(convABFM,-parameters_FM.MS.logPost(indFM(convABFM)),'o','Color',colvec(1,:),'MarkerSize',4);
    plot(convAFM,-parameters_FM.MS.logPost(indFM(convAFM)),'o','Color',colvec(1,:),'MarkerSize',4);
    plot(1:100,-bound*ones(100,1),':k')
    ylim([0 60])
    xlim([0 100])
    
%% FUa
colorind = 1;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));

colvecFUa = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];
subplot(ha(6))   
    hold on
    fill([0,1,1,0],[0,0,percentFUa(1),percentFUa(1)],colvecFUa(2,:));
    ylim([0 100]);
    box on;
    set(ha(6),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    text(0.2,50,[num2str(percentFUa(1)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(13))   
    hold on
    fill([0,1,1,0],[0,0,percentFUa(2),percentFUa(2)],colvecFUa(4,:));
    ylim([0 100]);
    box on;
    set(ha(13),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8,'Color',[0.96 0.96 0.96]);
    text(0.4,50,[num2str(percentFUa(2)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'Color',[0.75 0.75 0.75]);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(14))   
    hold on
    fill([0,1,1,0],[0,0,percentFUa(3),percentFUa(3)],colvecFUa(2,:));
    ylim([0 100]);
    box on;
    set(ha(14),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8,'Color',[0.95 0.95 0.95]);
    text(0.4,50,[num2str(percentFUa(3)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'Color',[0.75 0.75 0.75]);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(15))   
    hold on
    fill([0,1,1,0],[0,0,percentFUa(4),percentFUa(4)],colvecFUa(4,:));
    ylim([0 100]);
    box on;
    set(ha(15),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8,'Color',[0.95 0.95 0.95]);
    text(0.4,50,[num2str(percentFUa(4)), '%'],'FontName',setLay.ax.font,'FontSize',setLay.ax.size, 'Color',[0.75 0.75 0.75]);
    set(gcf,'renderer','opengl'); 
    
subplot(ha(1))
    plot(-parameters_FUa.MS.logPost(indFUa),'-o','Color',colvecFUa(2,:),'MarkerSize',4);
    hold on
    plot(1:100,-bound*ones(100,1),':k')
    
    text(2,-bound+2,'statstical threshold','FontName',setLay.ax.font,'Fontsize',6)

    ylim([0 60])
    
    set(ha(1),'Xtick',[0,50,100],'XtickLabel',{''},'Ytick',[0,20,40,60],'Fontsize',8) %
    ylabel(ha(1),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    set(ha(2),'Xtick',[0,50,100],'Ytick',[0,20,40,60],'XtickLabel',{''},'Fontsize',8)
    ylabel(ha(2),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    set(ha(3),'Xtick',[0,50,100],'Ytick',[0,20,40,60],'XtickLabel',{''},'Fontsize',8)
    ylabel(ha(3),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    set(ha(4),'Xtick',[0,50,100],'Ytick',[0,20,40,60],'XtickLabel',{''},'Fontsize',8)
    ylabel(ha(4),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    set(ha(5),'Xtick',[0,50,100],'Ytick',[0,20,40,60],'Fontsize',8)%length(globConvNM{j})
    ylabel(ha(5),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    xlabel(ha(5),'sorted optimizer runs','FontName',setLay.ax.font,'Fontsize',setLay.ax.size);
    set(ha(12),'Xtick',[0,1,2],'Ytick',[0,1,2],'XtickLabel',{''},'YtickLabel',{''},'Fontsize',8)
    
    set(ha(10),'XtickLabel',{''},'Ytick',[0 100],'Yticklabel',{''},'Fontsize',8);
    
%% Computation Time Boxplot
subplot(ha(11))
hold on;
    boxplot(log10([parameters_FUa.MS.t_cpu,parameters_FM.MS.t_cpu,parameters_FMs.MS.t_cpu,...
        parameters_SD{j}.MS.t_cpu,parameters_NM{j}.MS.t_cpu]),...
        'colors',[colvecFUa(2,:);cmp([2 5 3],:);colvecNM(2,:)],'symbol','+','outliersize',4);
    set(ha(11),'XTickLabel',{''},'YTick',log10([0.01:0.01:0.09,0.1:0.1:0.9,1:9,10:10:90]),...
        'YTickLabel',{'10^{-2}','','','','','','','','','10^{-1}',...
        '','','','','','','','','10^0','','','','','','','','','10^1','','','','','','','',''},'Fontsize',8,'TickLabelInterpreter', 'tex')
    ylabel('computation time for individual start [s]','FontName',setLay.ax.font,'FontSize',setLay.ax.size)
    set(findobj(gcf,'LineStyle','--'),'LineStyle','-')
%% Effective Computation Time    
subplot(ha(12))
    plot(0,t_effectiveFUa,'o','Color',colvecFUa(2,:))
    hold on
    plot([1.1,4],t_effectiveFM*ones(1,2),':k')
    plot(2*ones(2,1),[t_effectiveFM,t_effectiveFMs+1.3],'k')
    plot(3*ones(2,1),[t_effectiveFM,t_effectiveSD+1.3],'k')
    plot(4*ones(2,1),[t_effectiveFM,t_effectiveNM+1.2],'k')
    
    plot(2,t_effectiveFMs+1,'vk')
    plot(3,t_effectiveSD+1,'vk')
    plot(4,t_effectiveNM+0.9,'vk')
    
    plot(1,t_effectiveFM,'o','Color',cmp(2,:))
    plot(2,t_effectiveFMs,'o','Color',cmp(5,:))
    plot(3,t_effectiveSD,'o','Color',cmp(3,:))
    plot(4,t_effectiveNM,'o','Color',colvecNM(2,:))
    
    text(3.7,9.5,[num2str(round(t_effectiveFM/t_effectiveNM,2))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    text(2.7,9.5,[num2str(round(t_effectiveFM/t_effectiveSD,2))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    text(1.7,9.5,[num2str(round(t_effectiveFM/t_effectiveFMs,2))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    
    set(ha(12),'XTick',[0,1,2,3,4],'XTickLabel',{'unconstrained','constrained','hybrid','gradient descent','newton-type'},...
        'XTickLabelRotation',45,'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    ylabel({'average computation time'; 'per converged start [s]'},'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
     xlim([-0.5 4.5])
     ylim([0,13])
%% Fit     
subplot(ha(28))
    hf(7) = fill([1:6,6:-1:1],[squeeze(parameters_SD{j}.MS.sigmaInterval(1,indSD(j,convABSD{j}(1)),:));...
        flip(squeeze(parameters_SD{j}.MS.sigmaInterval(2,indSD(j,convABSD{j}(1)),:)))],[0.95 0.95 0.95],'Edgecolor',[0.90 0.90 0.90]);
    hold on
    hf(1:5) = plot(D.Ey,'ok','Markersize',2);
    hf(6) = plot(squeeze(Y_ODE_SD_opt(indSD(j,convABSD{j}(1)),:)),'-','Color',[0.8 0.8 0.8],'Linewidth',2);
    xlabel('NGF dose [nM]','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    ylabel('relative pErk [UI]','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    xlim([0.95 6.05])
    ylim([0.5 4.5])
    set(ha(28),'XTick',1:6,'XTickLabel',{'0','0.001','0.01','0.1','1','10'},'YTick',[1,2,3],...
        'FontName',setLay.ax.font,'Fontsize',8)

      hlf = legend(ha(28),[hf(1),hf(6),hf(7)],sprintf('measurement'),sprintf('simulation'),...
    sprintf('confidence bound'));
    set(hlf,'box','off','Position',[0.795, 0.21, 0.10, 0.06],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

% save PDF of Figure
feval('print', '-dpdf','-r300','Figure_NGFInducedErkSignaling.pdf');
