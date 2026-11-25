/**
 * AI 图片策略生成引擎
 * 自动识别项目类型，匹配图片策略，生成符合行业规范的图片
 */

class ImageStrategyEngine {
  constructor() {
    this.industryKeywords = {
      '电商零售': ['商品', '购买', '购物车', '价格', '商城', '店铺', 'SKU', '下单', '支付', '严选', '淘宝', '京东', '拼多多', '天猫', '网易严选', '小米有品'],
      '社区团购': ['团购', '团长', '自提', '生鲜', '买菜', '社区', '邻里', '拼团', '提货', '美团优选', '多多买菜', '兴盛优选'],
      '房产中介': ['房源', '二手房', '租房', '小区', '楼盘', '户型', '经纪人', '看房', '贝壳', '链家', '安居客', '房天下'],
      '招聘求职': ['职位', '简历', '面试', '公司', '招聘', '求职', 'HR', '猎头', 'BOSS直聘', '智联', '前程无忧', '拉勾'],
      '物流快递': ['快递', '运输', '配送', '仓储', '物流', '顺丰', '菜鸟', '京东物流', '骑手', '揽件', '派件', '中通', '圆通'],
      '餐饮外卖': ['菜品', '餐厅', '外卖', '美食', '订餐', '饿了么', '美团外卖', '堂食', '菜单', '厨师', '火锅', '烧烤'],
      '教育培训': ['课程', '老师', '学生', '学习', '培训', '教育', '网课', '在线学习', '作业', '考试', '新东方', '学而思'],
      '医疗健康': ['医院', '医生', '药品', '挂号', '问诊', '体检', '健康', '医疗', '好大夫', '丁香医生', '微医', '平安好医生'],
      '旅游出行': ['景点', '酒店', '机票', '攻略', '旅游', '旅行', '携程', '去哪儿', '飞猪', '民宿', '签证', '护照', '旅游网站', '旅游线路', '旅游团', '自由行', '跟团游', '周边游', '出境游', '国内游', '度假村', '温泉', '滑雪', '潜水', '露营', '自驾游'],
      '金融理财': ['理财', '基金', '股票', '保险', '投资', '金融', '支付宝', '微信支付', '银行', '证券', '余额宝'],
      '社交社区': ['动态', '帖子', '用户', '互动', '社区', '朋友圈', '微博', '小红书', '抖音', '内容', 'UGC', '粉丝'],
      '企业服务': ['SaaS', 'CRM', 'OA', '管理', '办公', '协同', '企业微信', '钉钉', '飞书', 'ERP', 'B端', '后台'],
      '上门按摩': ['按摩', '推拿', 'SPA', '足疗', '理疗', '技师', '上门按摩', '养生', '保健', '经络', '精油'],
      '生活服务': ['保洁', '家政', '月嫂', '保姆', '维修', '清洗', '搬家', '开锁', '疏通', '家政服务', '生活管家'],
      '上门服务': ['上门', '到家', '预约服务', '技师上门', '服务上门', '上门维修', '上门保洁', '上门美容'],
      '本地生活': ['同城', '本地', '附近', '周边', '吃喝玩乐', '本地服务', '同城配送', '即时配送', '闪送'],
      '美容美发': ['美容', '美发', '美甲', '美睫', '护肤', '理发', '造型', '美容院', '美发店', 'SPA'],
      '健身运动': ['健身', '瑜伽', '私教', '健身房', '运动', '跑步', '游泳', '普拉提', ' CrossFit'],
      '宠物服务': ['宠物', '遛狗', '宠物美容', '宠物医院', '寄养', '训犬', '宠物店', '猫咖', '狗咖'],
      '宠物用品': ['宠物用品', '宠物食品', '宠物玩具', '猫粮', '狗粮', '猫砂', '宠物零食', '宠物衣服', '宠物牵引绳', '猫爬架', '狗窝', '宠物保健品', '宠物药品', '水族', '仓鼠', '兔子', '鹦鹉'],
      '汽车服务': ['洗车', '保养', '维修', '代驾', '租车', '二手车', '4S店', '汽车美容', '充电桩'],
      '鲜花礼品': ['鲜花', '蛋糕', '礼品', '花店', '配送', '定制', '礼盒', '花束', '生日蛋糕'],
      '二手交易': ['二手', '闲置', '转转', '闲鱼', '跳蚤市场', '旧物', '回收', '置换', '古董'],
      '母婴服务': ['月嫂', '育儿', '产后', '催乳', '小儿推拿', '母婴护理', '月子中心', '早教'],
      '养老护理': ['养老', '护工', '陪护', '敬老院', '养老院', '居家养老', '老年护理', '康复'],
      '法律咨询': ['律师', '法律咨询', '合同', '纠纷', '诉讼', '仲裁', '法律顾问', '法律援助'],
      '装修设计': ['装修', '设计', '家装', '软装', '硬装', '设计师', '全屋定制', '装修公司']
    };

    this.imageStrategy = {
      '电商零售': {
        defaultType: '白底图',
        sceneType: '场景图',
        ratio: '1:1',
        style: 'minimalist',
        colorTemp: '5500K',
        keyFeatures: ['产品突出', '质感清晰', '背景干净'],
        businessPrompt: 'professional product photography'
      },
      '社区团购': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '1:1',
        style: 'authentic_lifestyle',
        colorTemp: '5200K',
        keyFeatures: ['有人物', '有社区感', '生鲜新鲜'],
        businessPrompt: 'authentic community lifestyle photography'
      },
      '房产中介': {
        defaultType: '实景图',
        sceneType: '房源实景',
        ratio: '16:9',
        style: 'real_estate',
        colorTemp: '5500K',
        keyFeatures: ['空间感', '明亮宽敞', '真实房源'],
        businessPrompt: 'real estate interior photography'
      },
      '招聘求职': {
        defaultType: '场景图',
        sceneType: '职场场景',
        ratio: '16:9',
        style: 'corporate',
        colorTemp: '5500K',
        keyFeatures: ['专业', '活力', '真实互动'],
        businessPrompt: 'professional corporate photography'
      },
      '物流快递': {
        defaultType: '场景图',
        sceneType: '工业场景',
        ratio: '16:9',
        style: 'industrial',
        colorTemp: '5600K',
        keyFeatures: ['规模化', '效率', '工作状态'],
        businessPrompt: 'industrial documentary photography'
      },
      '餐饮外卖': {
        defaultType: '场景图',
        sceneType: '美食场景',
        ratio: '1:1',
        style: 'food_photography',
        colorTemp: '4800K',
        keyFeatures: ['食欲感', '干净', '诱人'],
        businessPrompt: 'appetizing food photography'
      },
      '教育培训': {
        defaultType: '场景图',
        sceneType: '学习场景',
        ratio: '16:9',
        style: 'educational',
        colorTemp: '5500K',
        keyFeatures: ['互动', '专注', '有成果'],
        businessPrompt: 'authentic educational documentary'
      },
      '医疗健康': {
        defaultType: '场景图',
        sceneType: '医疗场景',
        ratio: '16:9',
        style: 'medical',
        colorTemp: '5800K',
        keyFeatures: ['专业', '温暖', '可信'],
        businessPrompt: 'professional medical environment photography'
      },
      '旅游出行': {
        defaultType: '场景图',
        sceneType: '风景场景',
        ratio: '16:9',
        style: 'travel',
        colorTemp: '5200K',
        keyFeatures: ['美丽', '向往', '真实'],
        businessPrompt: 'stunning travel photography'
      },
      '金融理财': {
        defaultType: '场景图',
        sceneType: '商务场景',
        ratio: '16:9',
        style: 'business',
        colorTemp: '6500K',
        keyFeatures: ['稳健', '专业', '安全'],
        businessPrompt: 'professional business concept photography'
      },
      '社交社区': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '1:1',
        style: 'lifestyle',
        colorTemp: '5200K',
        keyFeatures: ['真实', '多样', '有温度'],
        businessPrompt: 'authentic lifestyle photography'
      },
      '企业服务': {
        defaultType: '场景图',
        sceneType: '办公场景',
        ratio: '16:9',
        style: 'tech_office',
        colorTemp: '5500K',
        keyFeatures: ['现代', '高效', '专业'],
        businessPrompt: 'modern tech office photography'
      },
      '上门按摩': {
        defaultType: '场景图',
        sceneType: '服务场景',
        ratio: '3:4',
        style: 'wellness',
        colorTemp: '4800K',
        keyFeatures: ['放松', '专业', '私密舒适'],
        businessPrompt: 'professional wellness massage photography'
      },
      '生活服务': {
        defaultType: '场景图',
        sceneType: '服务场景',
        ratio: '16:9',
        style: 'service',
        colorTemp: '5200K',
        keyFeatures: ['整洁', '专业', '可信赖'],
        businessPrompt: 'professional home service photography'
      },
      '上门服务': {
        defaultType: '场景图',
        sceneType: '服务场景',
        ratio: '16:9',
        style: 'service',
        colorTemp: '5200K',
        keyFeatures: ['专业', '准时', '礼貌'],
        businessPrompt: 'professional on-demand service photography'
      },
      '本地生活': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '16:9',
        style: 'local_life',
        colorTemp: '5200K',
        keyFeatures: ['本地特色', '烟火气', '即时性'],
        businessPrompt: 'authentic local lifestyle photography'
      },
      '美容美发': {
        defaultType: '场景图',
        sceneType: '服务场景',
        ratio: '3:4',
        style: 'beauty',
        colorTemp: '5000K',
        keyFeatures: ['时尚', '精致', '蜕变'],
        businessPrompt: 'professional beauty salon photography'
      },
      '健身运动': {
        defaultType: '场景图',
        sceneType: '运动场景',
        ratio: '16:9',
        style: 'fitness',
        colorTemp: '5600K',
        keyFeatures: ['活力', '汗水', '坚持'],
        businessPrompt: 'dynamic fitness photography'
      },
      '宠物服务': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '1:1',
        style: 'pet',
        colorTemp: '5200K',
        keyFeatures: ['可爱', '温馨', '专业护理'],
        businessPrompt: 'warm pet care photography'
      },
      '宠物用品': {
        defaultType: '白底图',
        sceneType: '产品场景',
        ratio: '1:1',
        style: 'pet_product',
        colorTemp: '5500K',
        keyFeatures: ['产品突出', '可爱', '品质感'],
        businessPrompt: 'cute pet product photography'
      },
      '汽车服务': {
        defaultType: '场景图',
        sceneType: '工业场景',
        ratio: '16:9',
        style: 'automotive',
        colorTemp: '5800K',
        keyFeatures: ['专业', '精密', '可靠'],
        businessPrompt: 'professional automotive service photography'
      },
      '鲜花礼品': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '1:1',
        style: 'gift',
        colorTemp: '4800K',
        keyFeatures: ['浪漫', '精致', '惊喜'],
        businessPrompt: 'elegant gift and flower photography'
      },
      '二手交易': {
        defaultType: '白底图',
        sceneType: '产品场景',
        ratio: '1:1',
        style: 'minimalist',
        colorTemp: '5500K',
        keyFeatures: ['真实', '清晰', '无修饰'],
        businessPrompt: 'honest secondhand product photography'
      },
      '母婴服务': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '16:9',
        style: 'maternity',
        colorTemp: '5000K',
        keyFeatures: ['温柔', '专业', '安心'],
        businessPrompt: 'gentle maternal care photography'
      },
      '养老护理': {
        defaultType: '场景图',
        sceneType: '生活场景',
        ratio: '16:9',
        style: 'elderly_care',
        colorTemp: '5000K',
        keyFeatures: ['温暖', '关怀', '尊严'],
        businessPrompt: 'compassionate elderly care photography'
      },
      '法律咨询': {
        defaultType: '场景图',
        sceneType: '商务场景',
        ratio: '16:9',
        style: 'legal',
        colorTemp: '6000K',
        keyFeatures: ['专业', '严谨', '可信'],
        businessPrompt: 'professional legal service photography'
      },
      '装修设计': {
        defaultType: '场景图',
        sceneType: '实景图',
        ratio: '16:9',
        style: 'interior_design',
        colorTemp: '5500K',
        keyFeatures: ['设计感', '品质', '梦想家'],
        businessPrompt: 'stunning interior design photography'
      }
    };

    this.scenePrompts = {
      '白底图': 'clean white background, minimal shadows, product centered',
      '场景图': 'authentic lifestyle setting, natural environment, realistic context',
      '人物图': 'professional portrait, natural expression, appropriate attire',
      '实景图': 'real location photography, natural lighting, authentic setting',
      '工业场景': 'industrial environment, organized, professional documentation',
      '美食场景': 'appetizing presentation, warm lighting, food photography style',
      '学习场景': 'bright educational setting, engaged participants, natural light',
      '医疗场景': 'clean medical facility, professional environment, trustworthy',
      '风景场景': 'breathtaking landscape, golden hour, travel photography',
      '商务场景': 'professional corporate setting, modern office, business atmosphere',
      '生活场景': 'authentic daily life, natural moments, realistic setting',
      '服务场景': 'professional service moment, clean environment, trustworthy interaction',
      '运动场景': 'dynamic fitness environment, energetic atmosphere, motivational',
      '产品场景': 'clean product display, honest presentation, clear details'
    };

    this.stylePrompts = {
      'minimalist': 'minimalist Scandinavian style, clean lines, uncluttered',
      'authentic_lifestyle': 'authentic documentary style, genuine moments, real people',
      'real_estate': 'real estate photography, spacious feeling, wide angle',
      'corporate': 'professional corporate photography, modern business, confident',
      'industrial': 'industrial documentary, organized efficiency, scale',
      'food_photography': 'professional food photography, appetizing, vibrant colors',
      'educational': 'educational documentary, engaged learning, bright',
      'medical': 'medical photography, clean professional, trustworthy warmth',
      'travel': 'travel photography, stunning views, aspirational',
      'business': 'business concept photography, professional, secure',
      'lifestyle': 'lifestyle photography, authentic, diverse, warm',
      'tech_office': 'modern tech office photography, collaborative, productive',
      'wellness': 'wellness and spa photography, relaxing atmosphere, professional care',
      'service': 'professional service photography, trustworthy, efficient',
      'local_life': 'local lifestyle photography, neighborhood charm, authentic',
      'beauty': 'beauty and fashion photography, glamorous, transformative',
      'fitness': 'fitness and sports photography, energetic, motivational',
      'pet': 'pet photography, cute, heartwarming, professional care',
      'pet_product': 'cute pet product photography, adorable, playful, high quality',
      'automotive': 'automotive photography, precision, professional service',
      'gift': 'gift and lifestyle photography, elegant, romantic',
      'maternity': 'maternal and baby photography, gentle, nurturing',
      'elderly_care': 'elderly care photography, compassionate, dignified',
      'legal': 'legal and professional photography, authoritative, trustworthy',
      'interior_design': 'interior design photography, stylish, aspirational'
    };

    this.ratioParams = {
      '1:1': 'aspect ratio 1:1',
      '4:3': 'aspect ratio 4:3',
      '3:4': 'aspect ratio 3:4',
      '16:9': 'aspect ratio 16:9',
      '2:1': 'aspect ratio 2:1',
      '21:9': 'aspect ratio 21:9'
    };

    this.fallbackCSS = {
      '电商零售': 'background: linear-gradient(135deg, #f5f5f5, #e8e8e8); color: #999;',
      '社区团购': 'background: linear-gradient(135deg, #e8f5e9, #c8e6c9); color: #4caf50;',
      '房产中介': 'background: linear-gradient(135deg, #e3f2fd, #bbdefb); color: #2196f3;',
      '招聘求职': 'background: linear-gradient(135deg, #e8eaf6, #c5cae9); color: #3f51b5;',
      '物流快递': 'background: linear-gradient(135deg, #fff3e0, #ffe0b2); color: #ff9800;',
      '餐饮外卖': 'background: linear-gradient(135deg, #fce4ec, #f8bbd9); color: #e91e63;',
      '教育培训': 'background: linear-gradient(135deg, #e0f2f1, #b2dfdb); color: #009688;',
      '医疗健康': 'background: linear-gradient(135deg, #f3e5f5, #e1bee7); color: #9c27b0;',
      '旅游出行': 'background: linear-gradient(135deg, #e1f5fe, #b3e5fc); color: #03a9f4;',
      '金融理财': 'background: linear-gradient(135deg, #e8eaf6, #c5cae9); color: #1a237e;',
      '社交社区': 'background: linear-gradient(135deg, #f1f8e9, #dcedc8); color: #689f38;',
      '企业服务': 'background: linear-gradient(135deg, #eceff1, #cfd8dc); color: #546e7a;',
      '上门按摩': 'background: linear-gradient(135deg, #f3e5f5, #e1bee7); color: #7b1fa2;',
      '生活服务': 'background: linear-gradient(135deg, #e8f5e9, #c8e6c9); color: #388e3c;',
      '上门服务': 'background: linear-gradient(135deg, #fff3e0, #ffe0b2); color: #f57c00;',
      '本地生活': 'background: linear-gradient(135deg, #fce4ec, #f8bbd9); color: #c2185b;',
      '美容美发': 'background: linear-gradient(135deg, #f3e5f5, #e1bee7); color: #8e24aa;',
      '健身运动': 'background: linear-gradient(135deg, #e0f2f1, #b2dfdb); color: #00796b;',
      '宠物服务': 'background: linear-gradient(135deg, #fff8e1, #ffecb3); color: #ffa000;',
      '宠物用品': 'background: linear-gradient(135deg, #fff3e0, #ffe0b2); color: #ff9800;',
      '汽车服务': 'background: linear-gradient(135deg, #e3f2fd, #bbdefb); color: #1976d2;',
      '鲜花礼品': 'background: linear-gradient(135deg, #fce4ec, #f8bbd9); color: #d81b60;',
      '二手交易': 'background: linear-gradient(135deg, #f5f5f5, #e0e0e0); color: #616161;',
      '母婴服务': 'background: linear-gradient(135deg, #fce4ec, #f8bbd9); color: #c2185b;',
      '养老护理': 'background: linear-gradient(135deg, #fff3e0, #ffe0b2); color: #e65100;',
      '法律咨询': 'background: linear-gradient(135deg, #e8eaf6, #c5cae9); color: #283593;',
      '装修设计': 'background: linear-gradient(135deg, #e0f2f1, #b2dfdb); color: #00695c;'
    };
  }

  /**
   * Step 1: 识别项目类型
   */
  detectIndustry(input) {
    const text = input.toLowerCase();
    let bestMatch = { industry: '电商零售', score: 0 };

    for (const [industry, keywords] of Object.entries(this.industryKeywords)) {
      let score = 0;
      for (const keyword of keywords) {
        if (text.includes(keyword.toLowerCase())) {
          score += keyword.length; // 长关键词权重更高
        }
      }
      if (score > bestMatch.score) {
        bestMatch = { industry, score };
      }
    }

    return bestMatch.industry;
  }

  /**
   * Step 2: 匹配图片策略
   */
  getStrategy(industry) {
    return this.imageStrategy[industry] || this.imageStrategy['电商零售'];
  }

  /**
   * Step 3: 组装提示词
   */
  assemblePrompt(industry, subject, imageType, ratio) {
    const strategy = this.getStrategy(industry);
    
    // 基础指令
    const basePrompt = 'photorealistic, high quality, sharp focus, no AI artifacts';
    
    // 业务类型指令
    const businessPrompt = strategy.businessPrompt;
    
    // 主体描述
    const subjectPrompt = this.getSubjectPrompt(industry, subject);
    
    // 场景指令
    const scenePrompt = this.scenePrompts[imageType] || this.scenePrompts['场景图'];
    
    // 光线指令
    const lightPrompt = `soft natural lighting, color temperature ${strategy.colorTemp}`;
    
    // 风格指令
    const stylePrompt = this.stylePrompts[strategy.style];
    
    // 技术指令
    const techPrompt = 'shot on Canon EOS R5 with 50mm f/1.8 lens, film grain';
    
    // 去AI味指令
    const antiAIPrompt = 'no perfect symmetry, slight natural imperfections, realistic textures';
    
    // 比例指令
    const ratioPrompt = this.ratioParams[ratio] || 'aspect ratio 1:1';
    
    return `${businessPrompt}, ${subjectPrompt}, ${scenePrompt}, ${lightPrompt}, ${stylePrompt}, ${basePrompt}, ${techPrompt}, ${antiAIPrompt} ${ratioPrompt}`;
  }

  /**
   * 获取主体描述提示词
   */
  getSubjectPrompt(industry, subject) {
    const subjectMap = {
      '电商零售': `${subject} product, detailed, centered`,
      '社区团购': `fresh ${subject}, community setting, authentic`,
      '房产中介': `${subject} interior, spacious, bright`,
      '招聘求职': `professional ${subject}, modern office, collaborative`,
      '物流快递': `${subject} logistics, organized, efficient`,
      '餐饮外卖': `delicious ${subject}, appetizing, fresh`,
      '教育培训': `${subject} learning, engaged, bright classroom`,
      '医疗健康': `${subject} medical, professional, clean`,
      '旅游出行': `beautiful ${subject}, scenic, aspirational`,
      '金融理财': `${subject} business, professional, secure`,
      '社交社区': `authentic ${subject}, diverse people, genuine`,
      '企业服务': `${subject} technology, modern, collaborative`,
      '上门按摩': `professional ${subject} massage, relaxing, therapeutic`,
      '生活服务': `professional ${subject} service, clean, trustworthy`,
      '上门服务': `professional ${subject} on-demand service, punctual, courteous`,
      '本地生活': `local ${subject}, neighborhood charm, immediate`,
      '美容美发': `stylish ${subject} beauty service, glamorous, professional`,
      '健身运动': `energetic ${subject} fitness, dynamic, motivational`,
      '宠物服务': `cute ${subject} pet care, warm, professional`,
      '宠物用品': `adorable ${subject} pet product, cute design, high quality`,
      '汽车服务': `professional ${subject} automotive, precise, reliable`,
      '鲜花礼品': `elegant ${subject} gift, romantic, exquisite`,
      '二手交易': `honest ${subject} secondhand, clear, unmodified`,
      '母婴服务': `gentle ${subject} maternal care, nurturing, safe`,
      '养老护理': `compassionate ${subject} elderly care, warm, dignified`,
      '法律咨询': `professional ${subject} legal, authoritative, trustworthy`,
      '装修设计': `stylish ${subject} interior design, quality, dream home`
    };
    
    return subjectMap[industry] || `${subject}, detailed, realistic`;
  }

  /**
   * Step 4: 输出图片策略和提示词（不调用图片生成工具）
   */
  buildImageRequest(prompt, element, industry, imageType, ratio) {
    return { prompt, element, industry, imageType, ratio, status: 'prompt-ready' };
  }

  /**
   * Step 5: 质量检查
   */
  qualityCheck(image, industry) {
    const strategy = this.getStrategy(industry);
    const checks = {
      hasContent: !!image,
      correctFormat: image && (image.url || image.base64),
      reasonableSize: image && image.size && image.size < 2 * 1024 * 1024 // 2MB
    };
    
    return {
      passed: Object.values(checks).every(c => c),
      details: checks
    };
  }

  /**
   * Step 6: 降级方案
   */
  getFallback(industry, subject) {
    const css = this.fallbackCSS[industry];
    return {
      type: 'css_placeholder',
      content: `<div style="${css} width:100%; aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; border-radius:8px; font-size:24px; font-weight:700;">${subject.charAt(0)}</div>`,
      subject
    };
  }

  /**
   * 主执行函数
   */
  execute(projectDescription, elements) {
    const industry = this.detectIndustry(projectDescription);
    const strategy = this.getStrategy(industry);
    
    console.log(`识别行业: ${industry}`);
    console.log(`匹配策略:`, strategy);
    
    const results = [];
    
    for (const element of elements) {
      const imageType = element.type || strategy.defaultType;
      const ratio = element.ratio || strategy.ratio;
      
      // 组装提示词
      const prompt = this.assemblePrompt(industry, element.name, imageType, ratio);
      
      // 图片生成由宿主 AI 环境负责。此处只输出可交接的策略请求，不伪造图片结果。
      results.push(this.buildImageRequest(prompt, element.name, industry, imageType, ratio));
    }
    
    return {
      industry,
      strategy,
      images: results,
      summary: `已为 ${elements.length} 个素材需求输出图片策略与提示词；本引擎未生成图片，需由宿主环境调用可用图片能力`
    };
  }
}

// 导出引擎
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ImageStrategyEngine;
}

// 浏览器环境
if (typeof window !== 'undefined') {
  window.ImageStrategyEngine = ImageStrategyEngine;
}
