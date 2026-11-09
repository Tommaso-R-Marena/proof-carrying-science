%% Set-up
clear all; close all; clc

% page size
setLay.txt.width = 20.4;
setLay.txt.height = 29.1;

% font  
setLay.tit.size = 12;
setLay.tit.font = 'Times New Roman';
setLay.tit.weight = 'normal';

setLay.lab.size = 14;
setLay.lab.font = 'Helvetica';
setLay.lab.weight = 'bold';

setLay.ax.size = 10;
setLay.ax.font = 'Times New Roman';

%% Figure 5.2: Pom1p data
clc; close all; clearvars -except 'setLay'

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
text(.43,0.98,'B','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.01,0.51,'C','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);

ha(1) = axes('Position', [0.1, 0.66, 0.30, 0.30]);

ha(2) = axes('Position', [0.1, 0.28, 0.20, 0.20]);
ha(3) = axes('Position', [0.31, 0.28, 0.20, 0.20]);
ha(4) = axes('Position', [0.52, 0.28, 0.20, 0.20]);
ha(5) = axes('Position', [0.1, 0.06, 0.20, 0.20]);
ha(6) = axes('Position', [0.31, 0.06, 0.20, 0.20]);
ha(7) = axes('Position', [0.52, 0.06, 0.20, 0.20]);

ha(8) = axes('Position', [0.52, 0.66, 0.18, 0.30]);


%%
cmp = colormap(lines(6));

% load data
cur_dir = strrep(which('Figure_RafMekErk'),'Figure_RafMekErk.m','');
eval(['cd ' cur_dir]);

load('../Results/ResultManuscriptMS100_FM.mat') %constrained optimization
load('../Results/ResultManuscriptMS100_FMs.mat') %hybrid optimization
load('../Results/ResultManuscriptMS100_FUa.mat') %unconstrained optimization
load('../Results/ResultManuscriptMS100_SD.mat') %simulation-based optimization gradient descent
load('../Results/ResultManuscriptMS100_NM.mat') %simulation-based optimization newon-type
load('../Results/bestFit.mat')

sortConverged_RafMekErk
%% plot Convergence
colorind = 3;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
colvecSD = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

colorind = 4;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
colvecNM = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

colorind = 1;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
colvecFUa = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

colorind = 5;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
colvecFMs = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

colorind = 2;
add1 = 0.25*(1-cmp(colorind,:));
add2 = 0.5*(1-cmp(colorind,:));
add3 = 0.75*(1-cmp(colorind,:));
colvecFM = [cmp(colorind,:);cmp(colorind,:)+add1;cmp(colorind,:)+add2;cmp(colorind,:)+add3];

j=1;
subplot(ha(1))
    hc(1) = plot((1:100),-parameters_FUa.MS.logPost(indFUa),'-o','Color',colvecFUa(1,:),'MarkerSize',4);
    hold on
    
    hc(2) = plot((1:100),-parameters_FM.MS.logPost(indFM),'-o','Color',colvecFM(1,:),'MarkerSize',4);
    
    hc8 = plot((1:100),-parameters_FM.MS.logPost(indFM),'-o','Color',colvecFM(4,:),'MarkerSize',4);
    plot(convABFM,-parameters_FM.MS.logPost(indFM(convABFM)),'o','Color',colvecFM(1,:),'MarkerSize',4);
    plot(convAFM,-parameters_FM.MS.logPost(indFM(convAFM)),'o','Color',colvecFM(1,:),'MarkerSize',4);
    
    hc(4) = plot((1:100),-parameters_SD{j}.MS.logPost(indSD(j,:)),'-o','Color',colvecSD(1,:),'MarkerSize',4);
    
    plot((1:100),-parameters_SD{j}.MS.logPost(indSD(j,:)),'-o','Color',colvecSD(4,:),'MarkerSize',4);
    plot(convABSD{j},-parameters_SD{j}.MS.logPost(indSD(j,convABSD{j})),'o','Color',colvecSD(1,:),'MarkerSize',4);
    plot(convASD{j},-parameters_SD{j}.MS.logPost(indSD(j,convASD{j})),'o','Color',colvecSD(1,:),'MarkerSize',4);
    
    hc(5) = plot((1:100),-parameters_NM{j}.MS.logPost(indNM(j,:)),'-o','Color',colvecNM(1,:),'MarkerSize',4);
    
    plot((1:100),-parameters_NM{j}.MS.logPost(indNM(j,:)),'-o','Color',colvecNM(4,:),'MarkerSize',4);
    plot(convABNM{j},-parameters_NM{j}.MS.logPost(indNM(j,convABNM{j})),'o','Color',colvecNM(1,:),'MarkerSize',4);
    plot(convANM{j},-parameters_NM{j}.MS.logPost(indNM(j,convANM{j})),'o','Color',colvecNM(1,:),'MarkerSize',4);
    
    hc(3) = plot((1:100),-parameters_FMs.MS.logPost(indFMs),'-o','Color',colvecFMs(1,:),'MarkerSize',4);
    
    plot((1:100),-parameters_FMs.MS.logPost(indFMs),'-o','Color',colvecFMs(4,:),'MarkerSize',4);
    plot(convABFMs,-parameters_FMs.MS.logPost(indFMs(convABFMs)),'o','Color',colvecFMs(1,:),'MarkerSize',4);
    plot(convAFMs,-parameters_FMs.MS.logPost(indFMs(convAFMs)),'o','Color',colvecFMs(1,:),'MarkerSize',4);
    
    plot(1:5:100,-parameters_FUa.MS.logPost(indFUa(1:5:100)),'o','Color',colvecFUa(1,:),'MarkerSize',4);
    
    plot(convABFM(find(mod(convABFM,5)==2)),...
        -parameters_FM.MS.logPost(indFM(convABFM(find(mod(convABFM,5)==2)))),...
        'o','Color',colvecFM(1,:),'MarkerSize',4);
    plot(convAFM(find(mod(convAFM,5)==2)),...
        -parameters_FM.MS.logPost(indFM(convAFM(find(mod(convAFM,5)==2)))),...
        'o','Color',colvecFM(1,:),'MarkerSize',4);
    
    plot(convABFMs(find(mod(convABFMs,5)==3)),...
        -parameters_FMs.MS.logPost(indFMs(convABFMs(find(mod(convABFMs,5)==3)))),...
        'o','Color',colvecFMs(1,:),'MarkerSize',4);
    plot(convAFMs(find(mod(convAFMs,5)==3)),...
        -parameters_FMs.MS.logPost(indFMs(convAFMs(find(mod(convAFMs,5)==3)))),...
        'o','Color',colvecFMs(1,:),'MarkerSize',4);
    
    plot(convABSD{j}(mod(convABSD{j},5)==4),-parameters_SD{j}.MS.logPost(indSD(j,convABSD{j}(mod(convABSD{j},5)==4))),'o','Color',colvecSD(1,:),'MarkerSize',4);
    plot(convASD{j}(mod(convASD{j},5)==4),-parameters_SD{j}.MS.logPost(indSD(j,convASD{j}(mod(convASD{j},5)==4))),'o','Color',colvecSD(1,:),'MarkerSize',4);
    
    plot(convABNM{j}(mod(convABNM{j},5)==0),-parameters_NM{j}.MS.logPost(indNM(j,convABNM{j}(mod(convABNM{j},5)==0))),'o','Color',colvecNM(1,:),'MarkerSize',4);
    plot(convANM{j}(mod(convANM{j},5)==0),-parameters_NM{j}.MS.logPost(indNM(j,convANM{j}(mod(convANM{j},5)==0))),'o','Color',colvecNM(1,:),'MarkerSize',4);
    
    plot(1:100,-bound*ones(100,1),':k')
    box on;
    ylim([80 230])
    xlim([-0.1 100.1])
    
set(ha(1),'Xtick',[0,50,100],'Ytick',[100,140,180,220],'FontName',setLay.ax.font,'Fontsize',8)
ylabel(ha(1),'negative log-likelihood','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
xlabel(ha(1),'sorted optimizer runs','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

%% plot best fit SD
cmp2 = colormap(hsv(4));

ylab = {'relative pMek [UI]','','','relative pErk[UI]','',''};
title_vec = {'control','5 muM Sorafenib','30 muM UO126','','',''};
xlab = {'','','','time [h]','time [h]','time [h]'};
n_thetaDyn = 12;
ind = indconvASD{j}(indSD(j,1));
parameters = parameters_SD{j};
calculateSigmaInt_SDNM

for k=1:3
    maxMek(k) = max(max(bestFity{k}(:,1)/exp(parameters.MS.par(n_thetaDyn+1,ind))));
    maxErk(k) = max(max(bestFity{k}(:,2)/exp(parameters.MS.par(n_thetaDyn+2,ind))));
end
maxMekErk = repmat([max(maxMek) max(maxErk)],1,2);

D.plot{1} = D.measurement{1};
D.plot{1}(:,[3,4,7,8]) = NaN;
D.plot{2} = D.measurement{2};
D.plot{2}(1,[3,4,7,8]) = D.measurement{1}(1,[3,4,7,8]);
D.plot{3} = D.measurement{3};
D.plot{3}(1,[3,4,7,8]) = D.measurement{1}(1,[3,4,7,8]);

m=2;
for i=ind;
   for l=1:2
       for k=[1,3,2]
           subplot(ha(m))
           hf(6) = fill([bestFitt{k},fliplr(bestFitt{k})],[squeeze(parameters.MS.sigmaInterval{i,k}(:,l))/(exp(parameters.MS.par(n_thetaDyn+l,i))*maxMekErk(l))]',[0.95 0.95 0.95],'Edgecolor',[0.93 0.93 0.93]);
           hold on
           hf(5) = plot(bestFitt{k},bestFity{k}(:,l)/(exp(parameters.MS.par(n_thetaDyn+l,i))*maxMekErk(l)),'-','Color',[0.8 0.8 0.8],'Linewidth',2);
           hold on
           if k == 2 || k ==3
               hf(3) = plot(D.t{k}([1,3:end]),bsxfun(@rdivide,D.plot{k}([1,3:end],l+2),squeeze(exp(parameters.MS.par(n_thetaDyn+(l+2),i)))'*maxMekErk(l)),'>k','Markersize',2);
               hf(4) = plot(D.t{k}([1,3:end]),bsxfun(@rdivide,D.plot{k}([1,3:end],l+6),squeeze(exp(parameters.MS.par(n_thetaDyn+(l+6),i)))'*maxMekErk(l)),'xk','Markersize',2);
           else
               hf(1) = plot(D.t{k},bsxfun(@rdivide,D.plot{k}(:,l),squeeze(exp(parameters.MS.par(n_thetaDyn+(l),i)))'*maxMekErk(l)),'ok','Markersize',2);
               hf(2) = plot(D.t{k},bsxfun(@rdivide,D.plot{k}(:,l+4),squeeze(exp(parameters.MS.par(n_thetaDyn+(l+4),i)))'*maxMekErk(l)),'+k','Markersize',2);
           end
           ylabel(ylab{m-1},'FontName',setLay.ax.font,'FontSize',setLay.ax.size)
           title(title_vec{m-1},'FontName',setLay.ax.font,'FontSize',setLay.ax.size,'FontWeight',setLay.lab.weight)
           xlabel(xlab{m-1},'FontName',setLay.ax.font,'FontSize',setLay.ax.size)
           ylim([-0.2 1.5])
           xlim([-0.1 10.1])
           box on
        m=m+1;
       end
   end
end

set(ha(2),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'XtickLabel',{''},'FontName',setLay.ax.font,'Fontsize',8)
set(ha(3),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'XtickLabel',{''},'YtickLabel',{''},'FontName',setLay.ax.font,'Fontsize',8)
set(ha(4),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'XtickLabel',{''},'YtickLabel',{''},'FontName',setLay.ax.font,'Fontsize',8)
set(ha(5),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'FontName',setLay.ax.font,'Fontsize',8)
set(ha(6),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'YtickLabel',{''},'FontName',setLay.ax.font,'Fontsize',8)
set(ha(7),'Xtick',[0,2,4,6,8,10],'Ytick',[0,0.5,1,1.5],'YtickLabel',{''},'FontName',setLay.ax.font,'Fontsize',8)

subplot(ha(8))
    semilogy(0,t_effectiveFUa,'o','Color',colvecFUa(1,:))
    hold on
    
    semilogy([1.1,4],t_effectiveFM*ones(1,2),':k')
    semilogy(2*ones(2,1),[t_effectiveFM,t_effectiveFMs+1.8*100],'k')
    semilogy(3*ones(2,1),[t_effectiveFM,t_effectiveSD+2.6*100],'k')
    semilogy(4*ones(2,1),[t_effectiveFM,t_effectiveNM+2.9*100],'k')
    
    semilogy(2,t_effectiveFMs+1.2*100,'vk')
    semilogy(3,t_effectiveSD+2*100,'vk')
    semilogy(4,t_effectiveNM+2.2*100,'vk')
    
    semilogy(1,t_effectiveFM,'o','Color',colvecFM(1,:))
    semilogy(2,t_effectiveFMs,'o','Color',colvecFMs(1,:))
    semilogy(3,t_effectiveSD,'o','Color',colvecSD(1,:))
    semilogy(4,t_effectiveNM,'o','Color',colvecNM(1,:))
    
    text(3.6,490,['Factor ' ,num2str(round(t_effectiveFM/t_effectiveNM,1))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    text(2.6,490,['Factor ',num2str(round(t_effectiveFM/t_effectiveSD,1))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    text(1.6,490,['Factor ' ,num2str(round(t_effectiveFM/t_effectiveFMs,1))],'Rotation',90,'FontName',setLay.ax.font,'FontSize',9)
    
    set(ha(8),'XTick',[0,1,2,3,4],'XTickLabel',{'unconstrained','constrained','hybrid','gradient descent','newton-type'},...
         'XTickLabelRotation',45,'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
     ylabel({'average computation time'; 'per converged start [s]'},'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
     xlim([-0.3 4.3])
    
     
%% Legends    
     hlp = legend(ha(1),hc,sprintf('unconstrained\noptimization\nfmincon'),sprintf('constrained optimization\nfmincon'),...
    sprintf('hybrid optimization\nfmincon'),sprintf('simulation based\noptimization\ngradient descent'),sprintf('simulation based\noptimization\nnewton-type'));
    set(hlp,'box','off','Position',[0.78, 0.57, 0.16, 0.40],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size);
    
     hlf = legend(ha(3),hf,sprintf('blot 1'),...
    sprintf('blot 2'),sprintf('blot 3'),sprintf('blot 4'),sprintf('simulation'),sprintf('confidence bound'));
    set(hlf,'box','off','Position',[0.78, 0.18, 0.16, 0.20],'FontName',setLay.ax.font,'Fontsize',setLay.ax.size);

% save PDF of Figure
feval('print', '-dpdf','-r300','FigureRafMekErk.pdf');

%% Model comparison
ind = indconvASD{j}(indSD(j,1));

AIC_FB = 2*(-parameters_SD{j}.MS.logPost(ind)+(n_theta+n_sigma))
BIC_FB = 2*(-parameters_SD{j}.MS.logPost(ind))+(n_theta+n_sigma)*log(7*4+6*4+6*4)
     
load('../Results/ResultmodelComparisonFUa1000.mat')

[~,indFUa] = sort(parameters_FUa.MS.logPost,'descend');
ind = indFUa(1);

AIC_woFB = 2*(-parameters_FUa.MS.logPost(ind)+(n_theta+n_sigma))
BIC_woFB = 2*(-parameters_FUa.MS.logPost(ind))+(n_theta+n_sigma)*log(7*4+6*4+6*4)
 
diffAIC = AIC_FB - AIC_woFB
diffBIC = BIC_FB - BIC_woFB