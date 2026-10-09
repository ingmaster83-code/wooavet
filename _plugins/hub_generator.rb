require 'json'

module Jekyll
  module HubText
    module_function

    AMBIG = {}

    def hangul_tail?(s)
      c = s.to_s.strip.sub(/[\s\)\]\}\>'"”’.,!?~·\-]+\z/, '')[-1]
      !c.nil? && c.ord >= 0xAC00 && c.ord <= 0xD7A3
    end

    def batchim?(s)
      c = s.to_s.strip.sub(/[\s\)\]\}\>'"”’.,!?~·\-]+\z/, '')[-1]
      return false if c.nil?
      o = c.ord
      o >= 0xAC00 && o <= 0xD7A3 && (o - 0xAC00) % 28 != 0
    end

    def i_ga(w); hangul_tail?(w) ? w.to_s + (batchim?(w) ? '이' : '가') : "#{w}이(가)"; end
    def eun_neun(w); hangul_tail?(w) ? w.to_s + (batchim?(w) ? '은' : '는') : "#{w}은(는)"; end

    def sg_name(d, sg); AMBIG[sg] ? "#{d} #{sg}" : sg; end
    def dong_label(d); d == '기타' ? '기타 지역' : d; end
    def fmt(n); n.to_s.reverse.scan(/\d{1,3}/).join(',').reverse; end
  end

  class HubGenerator < Generator
    safe true
    priority :low

    NOUN = '동물병원'.freeze
    ICON = '🐾'.freeze
    PREFIX = 'vet'.freeze
    DETAIL_LAYOUT = 'vet'.freeze
    CAP = 200

    def generate(site)
      path = ['_rawdata', '_data_src'].map { |d| File.join(site.source, d, 'hub_items.json') }.find { |f| File.exist?(f) }
      return unless path
      items = JSON.parse(File.read(path, encoding: 'utf-8'))
      return if items.empty?

      HubText::AMBIG.clear
      items.group_by { |i| i['sigungu'] }.each { |sg, l| HubText::AMBIG[sg] = true if l.map { |i| i['doShort'] }.uniq.size > 1 }

      by_slug = items.each_with_object({}) { |i, h| h[i['slug']] = i }
      hub_sg = Hash.new { |h, k| h[k] = [] }
      counts = { sg: 0, dong: 0 }

      items.group_by { |i| i['doShort'] }.each do |do_short, d_items|
        d_items.group_by { |i| i['sigungu'] }.each do |sg, sg_items|
          sg_slug = sg_items.first['sgSlug']
          by_dong = sg_items.group_by { |i| i['dong'] }
          dongs = by_dong.map { |dg, l| { 'name' => dg, 'label' => HubText.dong_label(dg), 'count' => l.size } }
                         .sort_by { |h| h['name'] == '기타' ? [1, 0, ''] : [0, -h['count'], h['name']] }
          hub_sg[do_short] << { 'name' => sg, 'slug' => sg_slug, 'count' => sg_items.size }
          site.pages << HubSigunguPage.new(site, do_short, sg, sg_slug, sg_items, dongs)
          counts[:sg] += 1
          real = dongs.reject { |h| h['name'] == '기타' }
          by_dong.each do |dong, list|
            idx = real.index { |h| h['name'] == dong }
            prev_d = idx ? real[(idx - 1) % real.size]['name'] : nil
            next_d = idx ? real[(idx + 1) % real.size]['name'] : nil
            near = real.reject { |h| h['name'] == dong }.first(8)
            site.pages << HubDongPage.new(site, do_short, sg, sg_slug, dong, list, near, prev_d, next_d)
            counts[:dong] += 1
          end
        end
      end

      hub_sg.each_value { |v| v.sort_by! { |h| [-h['count'], h['name']] } }
      site.data['hub_sg'] = hub_sg

      # 상세 페이지에 동네 허브 링크 정보 주입
      site.pages.each do |p|
        next unless p.data['layout'] == DETAIL_LAYOUT
        it = by_slug[p.data['slug']]
        next unless it
        p.data['hub'] = { 'do' => it['doShort'], 'sigungu' => it['sigungu'], 'sgSlug' => it['sgSlug'], 'dong' => it['dong'],
                          'dongLabel' => HubText.dong_label(it['dong']), 'sgLabel' => HubText.sg_name(it['doShort'], it['sigungu']) }
      end
      Jekyll.logger.info 'HubGenerator:', "시군구 허브 #{counts[:sg]} / 동 허브 #{counts[:dong]}"
    end
  end

  class HubBasePage < Page
    def setup(site, dir, layout)
      @site = site
      @base = site.source
      @dir = dir
      @name = 'index.html'
      process(@name)
      read_yaml(File.join(@base, '_layouts'), "#{layout}.html")
      data['layout'] = layout
    end

    def seo(title, desc)
      data['title'] = title
      data['description'] = desc[0, 155]
    end

    def faq(pairs)
      data['faq'] = pairs.map { |q, a| { 'q' => q, 'a' => a } }
    end

    def stats(list)
      { 'n' => list.size, 'tel' => list.count { |i| i['tel'].to_s != '' } }
    end
  end

  class HubSigunguPage < HubBasePage
    def initialize(site, do_short, sg, sg_slug, items, dongs)
      setup(site, "region/#{do_short}/#{sg_slug}", 'hub_sg')
      sgn = HubText.sg_name(do_short, sg)
      st = stats(items)
      data['doShort'] = do_short
      data['sigungu'] = sg
      data['sgSlug'] = sg_slug
      data['sgLabel'] = sgn
      data['totalCount'] = items.size
      data['dongList'] = dongs
      data['items'] = items.sort_by { |i| [i['dong'], i['name']] }.first(60)
      top = dongs.reject { |h| h['name'] == '기타' }.first(3).map { |h| h['name'] }
      s = +"#{do_short} #{sg}에는 #{HubGenerator::NOUN} #{items.size}곳이 등록되어 있습니다."
      s << " #{top.join('·')} 일대에 많고," if top.size >= 2
      s << " 전화번호가 공공데이터에 등록된 곳은 #{st['tel']}곳입니다. 동네를 선택해 주소와 전화번호를 확인하세요."
      data['summary'] = s
      seo("#{sgn} #{HubGenerator::NOUN} #{items.size}곳 - 동네별 위치·전화번호",
          "#{do_short} #{sg}의 #{HubGenerator::NOUN} #{items.size}곳을 동네별로 확인하세요. 이름·주소·전화번호와 근처 동네 정보를 공공데이터로 안내합니다.")
      faq([["#{sg}에 #{HubGenerator::NOUN}은 몇 곳 있나요?", "공공데이터 기준 #{do_short} #{sg}에는 #{HubGenerator::NOUN} #{items.size}곳이 등록되어 있고, 전화번호가 있는 곳은 #{st['tel']}곳입니다."]])
    end
  end

  class HubDongPage < HubBasePage
    def initialize(site, do_short, sg, sg_slug, dong, list, near, prev_d, next_d)
      setup(site, "region/#{do_short}/#{sg_slug}/#{dong}", 'hub_dong')
      sgn = HubText.sg_name(do_short, sg)
      label = HubText.dong_label(dong)
      st = stats(list)
      data['doShort'] = do_short
      data['sigungu'] = sg
      data['sgSlug'] = sg_slug
      data['sgLabel'] = sgn
      data['dong'] = dong
      data['dongLabel'] = label
      data['totalCount'] = list.size
      data['truncated'] = list.size > HubGenerator::CAP
      data['items'] = list.sort_by { |i| i['name'] }.first(HubGenerator::CAP)
      data['near'] = near
      data['prevDong'] = prev_d
      data['nextDong'] = next_d
      s = +"#{do_short} #{sg} #{label}에는 #{HubGenerator::NOUN} #{list.size}곳이 등록되어 있습니다."
      s << " 이 중 전화번호가 공공데이터에 등록된 곳은 #{st['tel']}곳입니다."
      s << " 이름을 누르면 주소와 상세 정보를 볼 수 있습니다."
      data['summary'] = s
      seo("#{sgn} #{label} #{HubGenerator::NOUN} #{list.size}곳 - 주소·전화번호",
          "#{do_short} #{sg} #{label}의 #{HubGenerator::NOUN} #{list.size}곳 목록. 이름·주소·전화번호를 공공데이터 기준으로 확인하고 근처 동네도 찾아보세요.")
      pairs = [["#{label}에 #{HubGenerator::NOUN}은 몇 곳 있나요?", "공공데이터 기준 #{do_short} #{sg} #{label}에는 #{HubGenerator::NOUN} #{list.size}곳이 등록되어 있습니다."]]
      pairs << ["#{label} 근처 동네는 어디인가요?", "같은 #{sg}의 #{near.first(4).map { |h| "#{h['name']}(#{h['count']}곳)" }.join(', ')} 등을 함께 찾아보세요."] unless near.empty?
      faq(pairs)
    end
  end
end
